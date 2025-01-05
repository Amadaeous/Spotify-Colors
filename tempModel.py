import torch.nn as nn

class Encoder(nn.Module):
    def __init__(self, num_input_channels: int, base_channel_size: int, latent_dim: int, act_fn: object = nn.GELU):
        super().__init__()
        c_hid = base_channel_size
        self.net = nn.Sequential(
            nn.Conv1d(num_input_channels, c_hid, kernel_size=3, padding=1, stride=2),
            act_fn(),
            nn.Conv1d(c_hid, 2 * c_hid, kernel_size=3, padding=1, stride=2),
            act_fn(),
            nn.AvgPool1d(4),  # Reduce dimensionality
            nn.Flatten(),  # Image grid to single feature vector
            nn.Linear(2 * c_hid * 2048, latent_dim))

    def forward(self, x):
        return self.net(x)


class Decoder(nn.Module):
    def __init__(self, num_input_channels: int, base_channel_size: int, latent_dim: int, act_fn: object = nn.GELU):
        super().__init__()
        c_hid = base_channel_size
        self.linear = nn.Sequential(nn.Linear(latent_dim, 2 * c_hid * 2048), act_fn())
        self.upconv = nn.Sequential(
            nn.Conv1d(2 * c_hid, 2 * c_hid, kernel_size=3, padding=1),  # Increase dimensionality
            nn.Upsample(8192)  # Increase dimensionality
        )
        self.net = nn.Sequential(
            nn.ConvTranspose1d(2 * c_hid, c_hid, kernel_size=3, output_padding=1, padding=1, stride=2),
            act_fn(),
            nn.ConvTranspose1d(c_hid, num_input_channels, kernel_size=3, output_padding=1, padding=1, stride=2),
            nn.Tanh(),
        )

    def forward(self, x):
        x = self.linear(x)
        x = x.view(x.shape[0], -1, 2048)
        x = self.upconv(x)
        x = self.net(x)
        return x


class Autoencoder(nn.Module):
    def __init__(
        self,
        base_channel_size: int,
        latent_dim: int,
        encoder_class: object = Encoder,
        decoder_class: object = Decoder,
        num_input_channels: int = 3):
        super(Autoencoder, self).__init__()
        self.encoder = encoder_class(num_input_channels, base_channel_size, latent_dim)
        self.decoder = decoder_class(num_input_channels, base_channel_size, latent_dim)

    def forward(self, x):
        z = self.encoder(x)
        x_hat = self.decoder(z)
        return x_hat
