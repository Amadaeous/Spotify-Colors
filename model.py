import torch
import torch.nn as nn


class ActualModel(nn.Module):
    """
    this is the actual pytorch model class
    """
    def __init__(self):
        raise NotImplementedError

    def forward(self, x):
        raise NotImplementedError
