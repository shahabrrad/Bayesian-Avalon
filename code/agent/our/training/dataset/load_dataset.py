from torch.utils.data import Dataset, DataLoader
import torch
import json

from .generate_dataset_1 import vectorize_train_validation_test_sets as vectorize_data_1
from .generate_dataset_2 import vectorize_train_validation_test_sets as vectorize_data_2
import random


class MyGameDataset(Dataset):
    """
    Assumes each element in 'data_list' has the form:
      [label, discard1, discard2, discard3, discard4, discard5,
       input1, input2, ..., input15]
    and we want to return (features, label).
    """
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
        label = torch.tensor(label, dtype=torch.float)     # or torch.long if classification
        features = torch.tensor(features, dtype=torch.long)
        
        return features, label


def create_dataloaders(dataset_number=1,
                        train_percentage=0.8, 
                       batch_size=62910, #2048*8, 
                       shuffle=True):
    """
    1) Calls your 'vectorize_train_validation_sets' to get raw data.
    2) Wraps them in Dataset objects.
    3) Creates DataLoaders for training/validation.

    Returns:
        train_loader, val_loader
    """
    # Produce the raw data
    if dataset_number == 1:
        train_vectors, validation_vectors, test_vectors = vectorize_data_1(
            train_percentage=train_percentage
        )   # make suer the function is configured with circular and partial train and partial only validation
    elif dataset_number == 2:
        train_vectors, validation_vectors, test_vectors = vectorize_data_2(
            train_percentage=train_percentage
        )
    elif dataset_number == 12:
        train_vectors, validation_vectors, test_vectors = vectorize_data_1(
            train_percentage=train_percentage
        )
        train_vectors2, validation_vectors2, test_vectors2 = vectorize_data_2(
            train_percentage=train_percentage
        )
        train_vectors += train_vectors2
        validation_vectors += validation_vectors2
        test_vectors += test_vectors2

        random.shuffle(train_vectors)
        random.shuffle(validation_vectors)
        random.shuffle(test_vectors)

    # Build Datasets
    train_dataset = MyGameDataset(train_vectors)
    val_dataset   = MyGameDataset(validation_vectors)
    test_dataset  = MyGameDataset(test_vectors)  # if you need test dataset later

    # Build DataLoaders
    train_loader = DataLoader(train_dataset, 
                              batch_size=batch_size, 
                              shuffle=shuffle)
    val_loader   = DataLoader(val_dataset, 
                              batch_size=batch_size, 
                              shuffle=False)
    
    test_loader  = DataLoader(test_dataset,
                              batch_size=batch_size, 
                              shuffle=False)  # if you need test dataset later

    return train_loader, val_loader, test_loader