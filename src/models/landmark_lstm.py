import torch
import torch.nn as nn


class LandmarkBiLSTMClassifier(nn.Module):
    """
    MediaPipe landmark sequence -> BiLSTM -> KArSL class logits.

    Input shape: (B, T, F), where F is usually:
    - 75  for 25 pose landmarks x (x, y, z)
    - 99  for 33 pose landmarks x (x, y, z)
    - 132 for 33 pose landmarks x (x, y, z, visibility)
    """

    def __init__(
        self,
        input_dim: int = 75,
        num_classes: int = 502,
        hidden_size: int = 256,
        lstm_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        self.input_norm = nn.LayerNorm(input_dim)
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_size,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)
        out, _ = self.lstm(x)
        pooled = out.mean(dim=1)
        return self.classifier(pooled)
