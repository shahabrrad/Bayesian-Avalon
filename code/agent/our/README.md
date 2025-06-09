# Our agent structure
First we go through the files and folders here:

## pomegranate
A copy of the pomegranate package that is used for graphical inference with some changes. We added the ability to use a neural network as the function to be used as the factor function. We can use both max-product and sum-product algorithms for belief propagation. We have implemented two ways of training and using the graph: egocentric and non-egocentric model. With the egocentric model, the factor function input for every factor is changed in a way that the state vector that is used as input for the factor $f_i$ connected to player $p_i$ will always have player $i$ in the first index by doing circular shifts. By doing this we can use only one network in all 6 factor functions.
If you want to see the default pomegranate package, you can go to https://pomegranate.readthedocs.io/en/latest/


We have also added the ability to save neural networks and load them from the file so that we don't have to train it everytime.

## data_manager
This prepares and parses the data that is used for training the neuralnetworks in pomegranate model. You should clone the content of avalonlogs into it: https://github.com/WhoaWhoa/avalonlogs/tree/master
I am not currently using this because we have already trained the model and I have added the model in the models folder. Also the training functionality of the agent has not been implemented. We consider that the models are trained separately then passed to the agent. I will provide training script for the models as a TODO.

## base model
A base class that loads the factor graph and constructs it to be used by the agent. You can say this and the models that inherit from it are used as an interface between the agent and the graphical mdoel from pomegranate.


# models
This is where the files of the neural network will be saved so that we don't have to train them everytime. I have already added a file that was trained before into it.

# policy_models
These models can be used for selecting actions for the agent. So far we have only added a simple heuristic that votes against parties that have evil players in them.

# training
Includes the code used for the training of the neural network used for approximating the factor function. There is no need to rerun the training because the models are already provided