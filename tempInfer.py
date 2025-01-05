import torch
from tempModel import Autoencoder

def load_model() -> torch.nn.Module:
    state_dict = torch.load("tempmodel.pt")
    model = Autoencoder(base_channel_size=64, latent_dim=3, num_input_channels=31)
    model.load_state_dict(state_dict)
    return model

load_model()
