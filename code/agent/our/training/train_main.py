import matplotlib.pyplot as plt
import torch
from pomegranate.distributions import EgoNeuralDistribution
from torch.utils.data import Dataset, DataLoader
from torch import nn
import torch.nn.functional as F
import tqdm
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from temperature_scaling import ModelWithTemperature


from dataset.load_dataset import create_dataloaders


def get_predictions(model, dataloader, device):
    model.eval()
    all_probs = []
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            logits = model(inputs)
            probs = F.sigmoid(logits)

            # Predicted label: 1 if prob > 0.5
            preds = (probs >= 0.5).long()

            # Confidence is the prob assigned to the predicted class
            confs = probs * preds + (1 - probs) * (1 - preds)

            all_probs.append(confs.cpu())
            all_preds.append(preds.cpu())
            all_labels.append(labels.cpu())

    return torch.cat(all_probs), torch.cat(all_preds), torch.cat(all_labels)

def plot_accuracy_vs_confidence(confidences, predictions, labels, num_bins=10):
    bins = np.linspace(0.0, 1.0, num_bins + 1)
    bin_indices = np.digitize(confidences.numpy(), bins) - 1

    accuracies = []
    avg_confidences = []
    counts = []
    labels = labels.unsqueeze(1) 
    for i in range(num_bins):
        idx = bin_indices == i
        idx = torch.tensor(idx)
        if torch.sum(idx) > 0:
            acc = torch.mean((predictions[idx] == labels[idx]).float()).item()
            avg_conf = torch.mean(confidences[idx]).item()
            accuracies.append(acc)
            avg_confidences.append(avg_conf)
        else:
            accuracies.append(np.nan)
            avg_confidences.append((bins[i] + bins[i+1]) / 2)


    plt.figure(figsize=(6, 6))
    plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfect Calibration')
    plt.plot(avg_confidences, accuracies, marker='o', label='Model')
    plt.xlabel('Confidence')
    plt.ylabel('Accuracy')
    plt.title('Accuracy vs Confidence')
    plt.legend()
    plt.grid(True)
    # plt.show()
    plt.savefig("accuracy_vs_confidence_with_no_partial.png")


def predict_without_temperature(model, temperature_scaler, test_loader, device="cpu", is_multiclass=True):
    model.eval()
    temperature_scaler.eval()
    
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            
            logits = model(inputs)
            
            if is_multiclass:
                probs = F.softmax(logits, dim=1)
            else:
                probs = torch.sigmoid(logits)
            
            all_probs.append(probs.cpu())
            all_labels.append(labels) 
    
    all_probs = torch.cat(all_probs, dim=0)
    all_labels = torch.cat(all_labels, dim=0)
    return all_probs, all_labels



def draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, name, i):

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
    fig.savefig('metrics_on_full_game.png')



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


class MyGameDataset(Dataset):
    def __init__(self, data_list):
        super().__init__()
        self.data_list = data_list

    def __len__(self):
        return len(self.data_list)

    def __getitem__(self, idx):
        row = self.data_list[idx]
        # First element is the label
        label = row[0]
        # Remaining elements are the features
        features = row[6:]
        
        # Convert to PyTorch tensors
        label = torch.tensor(label, dtype=torch.float)
        features = torch.tensor(features, dtype=torch.long)
        
        return features, label



def compute_pos_weight(train_loader):
    """
    Computes the pos_weight = (num_negatives / num_positives)
    for binary classification based on the data in 'train_loader'.
    
    Returns:
        pos_weight (torch.Tensor): A single-element tensor
                                   suitable for nn.BCEWithLogitsLoss(pos_weight=...).
    """
    total_positives = 0
    total_count = 0

    # Iterate over the entire train dataset to count positives
    for _, batch_labels in train_loader:
        total_positives += batch_labels.sum().item()
        total_count += batch_labels.size(0)
    
    # number of negatives
    total_negatives = total_count - total_positives

    # Avoid division by zero
    if total_positives == 0:
        pos_weight_value = 1.0
    else:
        pos_weight_value = total_negatives / total_positives
    # pos_weight_value = 1.0
    return torch.tensor([pos_weight_value], dtype=torch.float)





if __name__ == "__main__":


    num_categories_list = [2, 16, 23, 3, 21, 23, 3, 16, 23, 3, 21, 23, 3, 16, 23, 3]
    embedding_dim_list = [4, 4, 1, 4, 4, 1, 4, 4, 1, 4, 4, 1, 4, 4, 1]  # Specify embedding dimensions for each variable

    hidden_dim = 16

    output_dim = 1
    EgoNeuralDistribution.initialize(num_categories_list, embedding_dim_list, hidden_dim, output_dim)
    model = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=0, from_file=True, graph=True)

    train_loader, val_loader, test_loader = create_dataloaders(dataset_number=12, 
                                                                train_percentage=0.8, 
                                                                batch_size=2048, #*8, #2048*8, #32, 
                                                                shuffle=True)
    

    

    print("length of training dataset", len(train_loader))
    print("length of validation dataset", len(val_loader))
    print("length of test dataset", len(test_loader))


    pos_weight = compute_pos_weight(train_loader)

    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.Adam(EgoNeuralDistribution.model.parameters(), lr=0.0001, weight_decay=1e-3) # added weight decay


    print("set the pos weights for the classes: ", pos_weight)

    train_losses = []
    val_losses = []
    val_losses_1 = []
    train_accuracies = []
    val_accuracies = []
    val_accuracies_1 = []
    train_f1_scores = []
    val_f1_scores = []
    val_f1_scores_1 = []

    early_stopping = EarlyStopping(patience=20, delta=0.01)
    # early_stopping = EarlyStopping(patience=20, delta=0.001)

    num_epochs = 500
    for epoch in tqdm.tqdm(range(num_epochs)):
        EgoNeuralDistribution.model.train()

        epoch_train_loss = 0.0
        epoch_train_correct = 0
        epoch_train_total = 0

        epoch_tp = 0
        epoch_fp = 0
        epoch_fn = 0
        epoch_tn = 0

        for batch_features, batch_labels in train_loader:

            outputs = EgoNeuralDistribution.model(batch_features)
            loss = criterion(outputs.squeeze(), batch_labels.float())
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            batch_size = batch_features.size(0)
            epoch_train_loss += loss.item() * batch_size

            outputs_sigmoid = torch.sigmoid(outputs)
            predicted_train = (outputs_sigmoid.squeeze() > 0.5).float()

            correct = (predicted_train == batch_labels.float()).sum().item()
            epoch_train_correct += correct
            epoch_train_total += batch_size
            
            tp = ((predicted_train == 1) & (batch_labels == 1)).sum().item()
            fp = ((predicted_train == 1) & (batch_labels == 0)).sum().item()
            fn = ((predicted_train == 0) & (batch_labels == 1)).sum().item()
            tn = ((predicted_train == 0) & (batch_labels == 0)).sum().item()
            
            epoch_tp += tp
            epoch_fp += fp
            epoch_fn += fn
            epoch_tn += tn

        epoch_train_loss /= epoch_train_total
        train_losses.append(epoch_train_loss)
        train_accuracy = epoch_train_correct / epoch_train_total
        train_accuracies.append(train_accuracy)   
        if epoch_tp == 0:
            train_f1 = 0.0
        else:
            precision = epoch_tp / (epoch_tp + epoch_fp + 1e-8)
            recall = epoch_tp / (epoch_tp + epoch_fn + 1e-8)
            train_f1 = 2 * (precision * recall) / (precision + recall + 1e-8)
        train_f1_scores.append(train_f1)

        #---------------------------------------------------
        # Validation Loop
        #---------------------------------------------------
        EgoNeuralDistribution.model.eval()
        with torch.no_grad():
            epoch_val_loss = 0.0
            epoch_val_correct = 0
            epoch_val_total = 0
            
            # For F1 computation of val_loader
            val_tp = 0
            val_fp = 0
            val_fn = 0
            val_tn = 0
            
            for val_features, val_labels in val_loader:
                val_outputs = EgoNeuralDistribution.model(val_features)
                val_loss = criterion(val_outputs.squeeze(), val_labels.float())
                
                # Accumulate validation loss
                batch_size = val_features.size(0)
                epoch_val_loss += val_loss.item() * batch_size
                
                # Predictions
                val_outputs_sigmoid = torch.sigmoid(val_outputs)
                predicted_val = (val_outputs_sigmoid.squeeze() > 0.5).float()
                
                correct_val = (predicted_val == val_labels.float()).sum().item()
                epoch_val_correct += correct_val
                epoch_val_total += batch_size
                
                tp = ((predicted_val == 1) & (val_labels == 1)).sum().item()
                fp = ((predicted_val == 1) & (val_labels == 0)).sum().item()
                fn = ((predicted_val == 0) & (val_labels == 1)).sum().item()
                tn = ((predicted_val == 0) & (val_labels == 0)).sum().item()
                
                val_tp += tp
                val_fp += fp
                val_fn += fn
                val_tn += tn
            

            epoch_val_loss /= epoch_val_total
            val_losses.append(epoch_val_loss)
            

            val_accuracy = epoch_val_correct / epoch_val_total
            val_accuracies.append(val_accuracy)
            
            if val_tp == 0:
                val_f1 = 0.0
            else:
                precision = val_tp / (val_tp + val_fp + 1e-8)
                recall = val_tp / (val_tp + val_fn + 1e-8)
                val_f1 = 2 * (precision * recall) / (precision + recall + 1e-8)
            val_f1_scores.append(val_f1)

            # Early stopping check
            val_loss_for_early_stopping = torch.tensor(epoch_val_loss)  # if needed
            early_stopping(val_loss_for_early_stopping, EgoNeuralDistribution.model)
            if early_stopping.early_stop:
                print(f"Early stopping at epoch {epoch}")
                print(
                f"Epoch [{epoch+1}/{num_epochs}], "
                f"Train Loss: {epoch_train_loss:.4f}, Val Loss: {epoch_val_loss:.4f}, "
                f"Train Acc: {train_accuracy:.4f}, Val Acc: {val_accuracy:.4f}"
                )
                break

        if (epoch + 1) % 5 == 0:
            print(
                f"Epoch [{epoch+1}/{num_epochs}], "
                f"Train Loss: {epoch_train_loss:.4f}, Val Loss: {epoch_val_loss:.4f}, "
                f"Train Acc: {train_accuracy:.4f}, Val Acc: {val_accuracy:.4f}"
            )


    early_stopping.load_best_model(EgoNeuralDistribution.model)
    print(f"Final train accuracy: {train_accuracies[-1]:.4f}, final val accuracy: {val_accuracies[-1]:.4f}")
    
    draw_graphs(train_losses, val_losses, train_accuracies, val_accuracies, train_f1_scores, val_f1_scores, "ego_centric_model", 0)


    scaled_model = ModelWithTemperature(EgoNeuralDistribution.model)
    scaled_model.set_temperature(val_loader)


    confidences, predictions, labels = get_predictions(EgoNeuralDistribution.model, val_loader, device=torch.device("cpu"))
    plot_accuracy_vs_confidence(confidences, predictions, labels)

    f1 = f1_score(labels.numpy(), predictions.numpy(), average='binary')
    accuracy = accuracy_score(labels.numpy(), predictions.numpy())
    precision = precision_score(labels.numpy(), predictions.numpy(), average='binary')
    recall = recall_score(labels.numpy(), predictions.numpy(), average='binary')
    print(f"F1 Score: {f1:.4f}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")

    confidences, predictions, labels = get_predictions(scaled_model, val_loader, device=torch.device("cpu"))
    plot_accuracy_vs_confidence(confidences, predictions, labels)


    print("--------------------------")
    f1 = f1_score(labels.numpy(), predictions.numpy(), average='binary')
    accuracy = accuracy_score(labels.numpy(), predictions.numpy())
    precision = precision_score(labels.numpy(), predictions.numpy(), average='binary')
    recall = recall_score(labels.numpy(), predictions.numpy(), average='binary')
    print(f"F1 Score: {f1:.4f}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")


    # Save the calibrated model to a file
    torch.save(scaled_model.state_dict(), "ego_model_2_calibrated.pth")
    print("Calibrated model saved as ego_model_2_calibrated.pth")


    # Save the uncalibrated model to a file
    torch.save(EgoNeuralDistribution.model.state_dict(), "ego_model_2_uncalibrated.pth")
    print("Uncalibrated model saved as ego_model_2_uncalibrated.pth")


