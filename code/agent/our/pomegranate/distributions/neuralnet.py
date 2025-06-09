# neuralnet.py

import torch

import torch.nn as nn
import torch.nn.functional as F

from .._utils import _cast_as_tensor
from .._utils import _update_parameter
from .._utils import _cast_as_parameter
from .._utils import _check_parameter
from .._utils import _reshape_weights

from ._distribution import Distribution
import os

# from data_manager import permutate_vector_for_player_order
# import ...data_manager.vectorize.permutate_vector_for_player_order

# def permutate_vector_for_player_order(args):
#     pass


class CategoricalNN(nn.Module):
    """The class that holds a neural network to be used for a high dimentional categorical distribution"""
    def __init__(
            self,
            num_categories_list,
            embedding_dim_list,
            hidden_dim,
            output_dim):
        """
        Args:
            num_categories_list (list of int): Number of categories for each categorical variable.
            embedding_dim_list (list of int): Dimension of the embedding for each categorical variable.
            hidden_dim (int): Dimension of the hidden layer.
            output_dim (int): Dimension of the output layer.
        """
        super(CategoricalNN, self).__init__()

        # Embedding layers for each categorical variable
        self.embeddings = nn.ModuleList([
            nn.Embedding(num_categories, embedding_dim)
            for num_categories, embedding_dim in zip(num_categories_list, embedding_dim_list)
        ])

        # FC layers
        total_embedding_dim = sum(embedding_dim_list)
        self.fc1 = nn.Linear(total_embedding_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

        # activation
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # Split input into separate categorical variables
        embedded = [self.embeddings[i](x[:, i])
                    for i in range(len(self.embeddings))]

        # concatenate embeddings
        x = torch.cat(embedded, dim=1)

        # FC layers
        x = self.relu(self.fc1(x))
        x = self.fc2(x)

        output = self.sigmoid(x)
        return output


class NeuralDistribution(Distribution):
    # TODO: define a probs parameter for the class
    """A base distribution object.

    This distribution is inherited by all the other distributions.
    input num_categories_list incluedes the categaries of all variables. The first variable is the output of the neural network
    This is saved into categories attribute of the class. meanwhile the num_categories_list attribute includes only the categories of the output variables
    """

    def __init__(
            self,
            num_categories_list,
            embedding_dim_list,
            hidden_dim,
            output_dim,
            name=None,
            # from_file=False,
            graph=False,
            inertia=0.0,
            frozen=False,
            check_data=True):
        super().__init__(inertia=inertia, frozen=frozen, check_data=check_data)
        self._device = _cast_as_parameter([0.0])

        _check_parameter(inertia, "inertia", min_value=0, max_value=1, ndim=0)
        _check_parameter(frozen, "frozen", value_set=[True, False], ndim=0)
        _check_parameter(check_data, "check_data", value_set=[True, False],
                         ndim=0)

        self.register_buffer("inertia", _cast_as_tensor(inertia))
        self.register_buffer("frozen", _cast_as_tensor(frozen))
        self.register_buffer("check_data", _cast_as_tensor(check_data))

        self._initialized = False
        # self.from_file = from_file
        self.name = name
        self.graph = graph
        self.trained = False

        if (num_categories_list[0] != 2) or (output_dim != 1): # TODO can this be changed to multiple categories if we change the network to be use softmax instead of sigmoid
            raise ValueError("The output variable should have two categories both in output_dim and in number of categories")

        self.num_categories_list = num_categories_list[1:]
        self.categories = num_categories_list
        self.embedding_dim_list = embedding_dim_list
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        

        self.model = CategoricalNN(
            self.num_categories_list,
            self.embedding_dim_list,
            hidden_dim,
            output_dim)

    @property
    def device(self):
        try:
            return next(self.parameters()).device
        except BaseException:
            return 'cpu'

    @property
    def dtype(self):
        return next(self.parameters()).dtype

    def freeze(self):
        self.register_buffer("frozen", _cast_as_tensor(True))
        return self

    def unfreeze(self):
        self.register_buffer("frozen", _cast_as_tensor(False))
        return self

    def forward(self, X):
        self.summarize(X)
        return self.log_probability(X)

    def backward(self, X):
        self.from_summaries()
        return X

    def _initialize(self, d):
        self.d = d
        self._reset_cache()

    def _reset_cache(self):  # Replaced this with just redefininh the model
        if not self._initialized:
            return

        self.model = CategoricalNN(
            self.num_categories_list,
            self.embedding_dim_list,
            self.hidden_dim,
            self.output_dim)


    def probability(self, X):
        """returns the probability fo X happening.
        X is the array of all variables connected to the factor, including the 0 index
        """

        model_input = torch.tensor([X[1:]])
        expected_output = torch.tensor(X[0])

        output = self.model(model_input).item()
        if expected_output == 1:
            return output
        else:
            return 1 - output


    # TODO - This funciton can be just the log of probability function. left unimplemented for now because it is not used
    def log_probability(self, X):
        raise NotImplementedError

    def fit(self, X, X_valid=None, sample_weight=None):
        self.summarize(X, X_valid=X_valid, sample_weight=sample_weight)
        self.from_summaries()
        # if self.from_file:
        #     file_path = self.name + ".pth"
        #     if not os.path.exists(file_path):
        #         torch.save(self.model.state_dict(), self.name+'.pth')
        return self

    def get_model(self):
        return self.model
    
    def set_model(self, model):
        self.model = model

    def load_from_file(self, folder_path):
        script_dir = "our/models/"
        file_path = os.path.join(script_dir, folder_path, self.name + ".pth")
        # file_path = folder_path + self.name + ".pth"
        if os.path.exists(file_path):
            self.model.load_state_dict(torch.load(file_path, weights_only=True))
            return
        else:
            print(file_path)
            print(os.path.abspath(file_path))
            raise ValueError("File not found for factor ", self.name)


    def summarize(self, X, X_valid=None, sample_weight=None, from_file=None, num_epochs=100):
        """Instead of extracting the sufficient statistics, we will train the model on the data."""
        if from_file:
            script_dir = "our/models/"
            file_path = os.path.join(script_dir, from_file, self.name + ".pth")
            # file_path = from_file + self.name + ".pth"
            if os.path.exists(file_path):
                self.model.load_state_dict(torch.load(file_path, weights_only=True))
                return
            else:
                print("File not found for factor ", self.name, " Training the model from scratch")

        if not self._initialized:
            self._initialize(len(X[0]))

        # X = _cast_as_tensor(X)
        # _check_parameter(X, "X", ndim=2, shape=(-1, self.d),
        #                  check_parameter=self.check_data)
        if X_valid is None:
            X_train = torch.stack([i[1:] for i in X[:-1000]], dim=0)
            Y_train = torch.stack([i[0] for i in X[:-1000]], dim=0)
            # print("x_train", X_train[0])
            # print("train_shape", X_train.shape)
            X_val = torch.stack([i[1:] for i in X[-1000:]], dim=0)
            Y_val = torch.stack([i[0] for i in X[-1000:]], dim=0)
        else:
            X_train = torch.stack([i[1:] for i in X], dim=0)
            Y_train = torch.stack([i[0] for i in X], dim=0)
            # print("x_train", X_train[0])
            # print("train_shape", X_train.shape)
            X_val = torch.stack([i[1:] for i in X_valid], dim=0)
            Y_val = torch.stack([i[0] for i in X_valid], dim=0)

        # Define loss function and optimizer
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)

        train_losses = []
        val_losses = []
        train_accuracies = []
        val_accuracies = []
        train_f1_scores = []
        val_f1_scores = []

        for epoch in range(num_epochs):
            # Forward pass
            outputs = self.model(X_train)
            loss = criterion(outputs.squeeze(), Y_train.float())

            # Backward pass and optimization
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_losses.append(loss.item())

            predicted_train = (outputs.squeeze() > 0.5).float()
            train_accuracy = (predicted_train == Y_train.float()).sum().item() / Y_train.size(0)
            train_accuracies.append(train_accuracy)


            tp = ((predicted_train == 1) & (Y_train == 1)).sum().item()
            fp = ((predicted_train == 1) & (Y_train == 0)).sum().item()
            fn = ((predicted_train == 0) & (Y_train == 1)).sum().item()
            # print(tp, fp, fn)
            if tp == 0:
                f1 = 0
            else:
                precision = tp / (tp + fp)
                recall = tp / (tp + fn)
                f1 = 2 * (precision * recall) / (precision + recall)
            train_f1_scores.append(f1)

            with torch.no_grad():
                val_outputs = self.model(X_val)
                val_loss = criterion(val_outputs.squeeze(), Y_val.float())
                val_losses.append(val_loss.item())
                predicted = (val_outputs.squeeze() > 0.5).float()
                accuracy = (predicted == Y_val.float()
                            ).sum().item() / Y_val.size(0)
                val_accuracies.append(accuracy)

                tp = ((predicted == 1) & (Y_val == 1)).sum().item()
                fp = ((predicted == 1) & (Y_val == 0)).sum().item()
                fn = ((predicted == 0) & (Y_val == 1)).sum().item()
                # print(tp, fp, fn)
                if tp == 0:
                    f1 = 0
                else:
                    precision = tp / (tp + fp)
                    recall = tp / (tp + fn)
                    f1 = 2 * (precision * recall) / (precision + recall)
                val_f1_scores.append(f1)

            if (epoch + 1) % 10 == 0:
                print(
                    f'Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}')

                print(f'Validation Accuracy: {accuracy:.4f}')

                print(f'Validation Loss: {val_loss.item():.4f}')

        if self.graph:
            draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, self.name)

        if from_file:
            file_path = from_file + self.name + ".pth"
            if not os.path.exists(file_path):
                torch.save(self.model.state_dict(), self.name+'.pth')
        
        self.trained = True

        return X, sample_weight

    def from_summaries(self):   # We dont need this when replacing summary statistics with neural network
        return
        # raise NotImplementedError


class ConditionalDistribution(Distribution):
    def __init__(self, inertia, frozen, check_data):
        super().__init__(inertia=inertia, frozen=frozen, check_data=check_data)

    def marginal(self, dim):
        raise NotImplementedError


def draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, name):
    """This function can be used to draw the training graphs"""
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(30, 10))

    axs[0].plot(train_losses, label='Train')
    axs[0].plot(val_losses, label='Validation')
    axs[0].set_title('Loss '+name)
    axs[0].legend()

    axs[1].plot(train_accuracies, label='Train')
    axs[1].plot(val_accuracies, label='Validation')
    axs[1].set_title('Accuracy '+name)
    axs[1].legend()

    axs[2].plot(train_f1_scores, label='Train')
    axs[2].plot(val_f1_scores, label='Validation')
    axs[2].set_title('F1 Score '+name)
    axs[2].legend()

    fig.savefig(name + '_metrics.png')
