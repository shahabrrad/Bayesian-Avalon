# egocentric_neuralnet.py

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

from itertools import combinations

from .temperature_scaling import ModelWithTemperature


class EarlyStopping:
    def __init__(self, patience=10, delta=0):
        self.patience = patience
        self.delta = delta
        self.best_score = None
        self.early_stop = False
        self.counter = 0
        self.best_model_state = None

    def __call__(self, val_loss, model):
        score = -val_loss
        if self.best_score is None:
            self.best_score = score
            self.best_model_state = model.state_dict()
        elif score < self.best_score + self.delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.best_model_state = model.state_dict()
            self.counter = 0

    def load_best_model(self, model):
        model.load_state_dict(self.best_model_state)


class CategoricalNN(nn.Module):
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
        self.fc_between = nn.Linear(hidden_dim, hidden_dim)  # TODO this can be used to change the network structure
        self.fc2 = nn.Linear(hidden_dim, output_dim)

        # activation
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # This change was made to ensure that 0 input does not affect the gradients
        embedded = []
        for i, embedding in enumerate(self.embeddings):
            missing_idx = 0
            
            e_i = embedding(x[:, i])               # [batch_size, embedding_dim]
            
            # Create a mask: 1 if not missing, 0 if missing
            mask_i = (x[:, i] != missing_idx).float()  # [batch_size]
            mask_i = mask_i.unsqueeze(-1)              # [batch_size, 1]
            
            # Multiply out if missing
            e_i = e_i * mask_i
            
            embedded.append(e_i)

        x = torch.cat(embedded, dim=1)

        # FC layers
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc_between(x))
        x = self.fc2(x)

        return x


class EgoNeuralDistribution(Distribution):
    """A base distribution object.

    This distribution is inherited by all the other distributions.
    input num_categories_list incluedes the categaries of all variables. The first variable is the output of the neural network
    This is saved into categories attribute of the class. meanwhile the num_categories_list attribute includes only the categories of the output variables
    """

    # static variables to hold the model for all instances of the factor function
    # these values will be shared among all instances of the factor function
    model = None
    trained = False
    
    @classmethod
    def initialize(cls, num_categories_list,
                    embedding_dim_list,
                    hidden_dim,
                    output_dim):
        # cls.static_var = custom_value
        num_categories_list = num_categories_list[1:]
        categories = num_categories_list
        embedding_dim_list = embedding_dim_list
        hidden_dim = hidden_dim
        output_dim = output_dim

        calibrated = True # This will determine if we are using the calibrated model or not
        cls.model = CategoricalNN(
                num_categories_list,
                embedding_dim_list,
                hidden_dim,
                output_dim)
        cls.calibrated_model = ModelWithTemperature(cls.model)

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
        assert self.name is not None, "Name of the factor function is not provided"
        assert self.name in [0,1,2,3,4,5], "the name of the factor function should be its corresponding index in the order of the players"
        self.graph = graph

        if (num_categories_list[0] != 2) or (output_dim != 1): # this can be changed to multiple categories if we change the network to be use softmax instead of sigmoid
            raise ValueError("The output variable should have two categories both in output_dim and in number of categories")

        self.num_categories_list = num_categories_list[1:]
        self.categories = num_categories_list
        self.embedding_dim_list = embedding_dim_list
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        self.calibrated = True
        
        

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

    def _reset_cache(self):  # Replaced this with just redefine the model
        if not self._initialized:
            return

        EgoNeuralDistribution.model = CategoricalNN(
            self.num_categories_list,
            self.embedding_dim_list,
            self.hidden_dim,
            self.output_dim)
        
        EgoNeuralDistribution.calibrated_model = ModelWithTemperature(EgoNeuralDistribution.model)


    def probability(self, X):
        """returns the probability fo X happening.
        X is the array of all variables connected to the factor, including the 0 index
        """

        if self.calibrated:
            EgoNeuralDistribution.calibrated_model.eval()
        else:
            EgoNeuralDistribution.model.eval()

        with torch.no_grad():
            model_input = torch.tensor([permutate_vector_for_player_order(X, int(self.name))[1:]])
            expected_output = torch.tensor(X[0])

            if self.calibrated:
                output = EgoNeuralDistribution.calibrated_model(model_input)
            else:
                output = EgoNeuralDistribution.model(model_input)
            output = torch.sigmoid(output).item()

        if expected_output == 1:
            return output
        else:
            return 1 - output


    # This funciton can be just the log of probability function. left unimplemented for now because it is not used
    def log_probability(self, X):
        raise NotImplementedError

    def fit(self, X, X_valid=None, sample_weight=None):
        self.summarize(X, X_valid=X_valid, sample_weight=sample_weight, i=0)
        self.from_summaries()
        return self
    
    def load_from_file(self, folder_path):
        print("Calibration status: ", self.calibrated)
        script_dir = "our/models/"
        if not self.calibrated:
            file_path = os.path.join(script_dir, folder_path, "ego_centric_model.pth" )
        else:
            file_path = os.path.join(script_dir, folder_path, "ego_model_2_calibrated.pth" )


        # file_path = folder_path + "ego_centric_model" + ".pth"
        if os.path.exists(file_path):
            if not self.calibrated:
                self.model.load_state_dict(torch.load(file_path, weights_only=True))
            else:
                self.calibrated_model.load_state_dict(torch.load(file_path, weights_only=True))
            return
        else:
            raise ValueError("File not found for factor ", self.name)


    def summarize(self, X, X_valid=None, sample_weight=None, from_file=None, num_epochs=500, i=0):
        """Instead of extracting the sufficient statistics, we will train the model on the data."""
        if from_file:
            script_dir = "our/models/"
            if self.calibrated:
                file_path = os.path.join(script_dir, from_file, "ego_model_2_calibrated.pth" )

                if os.path.exists(file_path):
                    EgoNeuralDistribution.calibrated_model.load_state_dict(torch.load(file_path, weights_only=True))
                    return
                else:
                    
                    print("File not found for factor ", file_path, " Training the model from scratch")
            else:
                file_path = os.path.join(script_dir, from_file, "ego_centric_model.pth" )

                if os.path.exists(file_path):
                    EgoNeuralDistribution.model.load_state_dict(torch.load(file_path, weights_only=True))
                    return
                else:
                    
                    print("File not found for factor ", file_path, " Training the model from scratch")

        if EgoNeuralDistribution.trained:
            print("Egocentric model already trained")
            return
        
        if not self._initialized:
            self._initialize(len(X[0]))


        if X_valid is None:
            X_train = torch.stack([i[1:] for i in X[:-1000]], dim=0)
            Y_train = torch.stack([i[0] for i in X[:-1000]], dim=0)

            X_val = torch.stack([i[1:] for i in X[-1000:]], dim=0)
            Y_val = torch.stack([i[0] for i in X[-1000:]], dim=0)
        else:
            X_train = torch.stack([i[1:] for i in X], dim=0)
            Y_train = torch.stack([i[0] for i in X], dim=0)

            X_val = torch.stack([i[1:] for i in X_valid], dim=0)
            Y_val = torch.stack([i[0] for i in X_valid], dim=0)

        # Define loss function and optimizer
        # criterion = nn.BCELoss()
        total_samples = len(Y_train)
        num_samples_in_class_0 = (Y_train == 0).sum().item()
        num_samples_in_class_1 = (Y_train == 1).sum().item()

        weight_for_class_0 = total_samples / (num_samples_in_class_0 * 2)
        weight_for_class_1 = total_samples / (num_samples_in_class_1 * 2)


        pos_weight_value = num_samples_in_class_0 / num_samples_in_class_1  
        pos_weight = torch.tensor([pos_weight_value], dtype=torch.float)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        # optimizer = torch.optim.Adam(EgoNeuralDistribution.model.parameters(), lr=0.01)
        optimizer = torch.optim.Adam(EgoNeuralDistribution.model.parameters(), lr=0.001)


        print("set the weights for the classes: ", weight_for_class_0, weight_for_class_1)

        train_losses = []
        val_losses = []
        train_accuracies = []
        val_accuracies = []
        train_f1_scores = []
        val_f1_scores = []

        # early_stopping = EarlyStopping(patience=20, delta=0.01)
        early_stopping = EarlyStopping(patience=20, delta=0.001)


        for epoch in range(num_epochs):
            # Forward pass
            outputs = EgoNeuralDistribution.model(X_train)
            loss = criterion(outputs.squeeze(), Y_train.float())

            # Backward pass and optimization
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_losses.append(loss.item())

            outputs = torch.sigmoid(outputs)

            predicted_train = (outputs.squeeze() > 0.5).float()
            train_accuracy = (predicted_train == Y_train.float()).sum().item() / Y_train.size(0)
            train_accuracies.append(train_accuracy)


            tp = ((predicted_train == 1) & (Y_train == 1)).sum().item()
            fp = ((predicted_train == 1) & (Y_train == 0)).sum().item()
            fn = ((predicted_train == 0) & (Y_train == 1)).sum().item()
            tn = ((predicted_train == 0) & (Y_train == 0)).sum().item()
            print_train = ('tp:', tp, 'fp:', fp, 'fn:', fn, 'tn:', tn)

            if tp == 0:
                f1 = 0
            else:
                precision = tp / (tp + fp)
                recall = tp / (tp + fn)
                f1 = 2 * (precision * recall) / (precision + recall)
            train_f1_scores.append(f1)

            with torch.no_grad():
                val_outputs = EgoNeuralDistribution.model(X_val)
                val_loss = criterion(val_outputs.squeeze(), Y_val.float())
                val_losses.append(val_loss.item())
                val_outputs = torch.sigmoid(val_outputs)
                predicted = (val_outputs.squeeze() > 0.5).float()
                accuracy = (predicted == Y_val.float()
                            ).sum().item() / Y_val.size(0)
                val_accuracies.append(accuracy)

                tp = ((predicted == 1) & (Y_val == 1)).sum().item()
                fp = ((predicted == 1) & (Y_val == 0)).sum().item()
                fn = ((predicted == 0) & (Y_val == 1)).sum().item()
                tn = ((predicted == 0) & (Y_val == 0)).sum().item()
                print_valid = ('tp:', tp, 'fp:', fp, 'fn:', fn, 'tn:', tn)
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
                print("train state: ", print_train)
                print("valid state: ", print_valid)
            early_stopping(val_loss, EgoNeuralDistribution.model)
            if early_stopping.early_stop:
                print("Early stopping at epoch ", epoch)
                break
        early_stopping.load_best_model(EgoNeuralDistribution.model)
        print("final train state: ", print_train)
        print("final valid state: ", print_valid)

        if self.graph:
            draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, self.name, i)

        if from_file:
            if not self.calibrated:
                file_path = from_file + "ego_centric_model"+ ".pth"
            else:
                file_path = from_file + "ego_model_2_calibrated"+ ".pth"
            if not os.path.exists(file_path):
                torch.save(EgoNeuralDistribution.model.state_dict(), file_path)

        EgoNeuralDistribution.trained = True
        return X, sample_weight

    def from_summaries(self): 
        return
        # raise NotImplementedError


class ConditionalDistribution(Distribution):
    def __init__(self, inertia, frozen, check_data):
        super().__init__(inertia=inertia, frozen=frozen, check_data=check_data)

    def marginal(self, dim):
        raise NotImplementedError


def draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, name, i):
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(30, 10))

    name = "ego_centric_model"

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



def cyclic_perm(a):
    n = len(a)
    b = [[a[i - j] for i in range(n)] for j in range(n)]
    return b

def permutate_vector_for_player_order(vector, player_order):
    """changes the ordering of the game vector to become 'ego centric' for the player in order"""
    # the vector only has the player in index 0, the rest are game history
    # in this code I have considered that a zero number means "unknown" for the partials
    if player_order == 0:
        return vector
    
    new_vector = [vector[0]] + [0, 0, 0] * 5
    
    first_quest = [vector[1], vector[2], vector[3]]
    second_quest = [vector[4], vector[5], vector[6]]
    third_quest = [vector[7], vector[8], vector[9]]
    fourth_quest = [vector[10], vector[11], vector[12]]
    fifth_quest = [vector[13], vector[14], vector[15]]

    quests = [first_quest, second_quest, third_quest, fourth_quest, fifth_quest]

    #replace the quest outcomes
    for i in range(len(quests)):
        new_vector[3 + (i*3)] = quests[i][2]

    players = [0,1,2,3,4,5]
    player_permutations = cyclic_perm(players)
    ego_permutation = player_permutations[-1 * player_order]

    # replace the votes for the new composition
    old_vote_compositions = []
    new_vote_compositions = []
    for L in range(4, 6 + 1):
        for subset in combinations(players, L):
            old_vote_compositions.append(set(subset))
        for new_subset in combinations(ego_permutation, L):
            new_vote_compositions.append(set(new_subset))
    
    new_votes = []
    for i in range(len(quests)):
        quest = quests[i]
        if quest[1] != 0:
            old_vots = old_vote_compositions[quest[1] - 1]

            new_vote = new_vote_compositions.index(old_vots) + 1
        else:
            new_vote = 0
        new_vector[2 + (i*3)] = new_vote

    
    # replace the party for the 2p party
    old_2p_compositions = []
    new_2p_compositions = []
    # for L in range(6 + 1):
    for subset in combinations(players, 2):
        old_2p_compositions.append(set(subset))
    for new_subset in combinations(ego_permutation, 2):
        new_2p_compositions.append(set(new_subset))

    if quests[0][0] != 0:
        old_comp = old_2p_compositions[quests[0][0] - 1]
        new_vector[1] = new_2p_compositions.index(old_comp) + 1
    else:
        new_vector[1] = 0


    # replace the party for the 3-player parties (quest 2 and 4)
    old_3p_compositions = []
    new_3p_compositions = []
    for subset in combinations(players, 3):
        old_3p_compositions.append(set(subset))
    for new_subset in combinations(ego_permutation, 3):
        new_3p_compositions.append(set(new_subset))
    
    #quest 2:
    if quests[1][0] != 0:
        old_comp = old_3p_compositions[quests[1][0] - 1]
        new_vector[4] = new_3p_compositions.index(old_comp) + 1
    else:
        new_vector[4] = 0

    #quest 4:
    if quests[3][0] != 0:
        old_comp = old_3p_compositions[quests[3][0] - 1]
        new_vector[10] = new_3p_compositions.index(old_comp) + 1
    else:
        new_vector[10] = 0
    

    # replace the party for the 4-player parties (quest 3 and 5)
    old_4p_compositions = []
    new_4p_compositions = []
    for subset in combinations(players, 4):
        old_4p_compositions.append(set(subset))
    for new_subset in combinations(ego_permutation, 4):
        new_4p_compositions.append(set(new_subset))
    
    #quest 3:
    if quests[2][0] != 0:
        old_comp = old_4p_compositions[quests[2][0] - 1]
        new_vector[7] = new_4p_compositions.index(old_comp) + 1
    else:
        new_vector[7] = 0

    #quest 5:
    if quests[4][0] != 0:
        old_comp = old_4p_compositions[quests[4][0] - 1]
        new_vector[13] = new_4p_compositions.index(old_comp) + 1
    else:
        new_vector[13] = 0
    
    # print(vector)
    return new_vector