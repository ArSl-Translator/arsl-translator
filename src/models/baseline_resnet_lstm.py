import torch
import torch.nn as nn
import torchvision.models as models


class ResNetLSTMClassifier(nn.Module):
    """
    Frames -> ResNet18 (features) -> BiLSTM -> classifier
    Input:  x of shape (B, T, 3, H, W)
    Output: logits of shape (B, num_classes)
    """
    def __init__(
        self,
        num_classes: int = 502,
        backbone: str = "resnet18",
        pretrained: bool = True,
        lstm_hidden: int = 256,
        lstm_layers: int = 1,
        dropout: float = 0.2,
    ):
        super().__init__()

        if backbone == "resnet18":
            net = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
            feat_dim = net.fc.in_features  # 512
            net.fc = nn.Identity()
            self.cnn = net
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        self.lstm = nn.LSTM(
            input_size=feat_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(lstm_hidden * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, C, H, W)
        b, t, c, h, w = x.shape
        x = x.view(b * t, c, h, w)

        feats = self.cnn(x)          # (B*T, feat_dim)
        feats = feats.view(b, t, -1) # (B, T, feat_dim)

        out, _ = self.lstm(feats)    # (B, T, 2*lstm_hidden)

        # Use last timestep (works well for isolated signs)
        last = out[:, -1, :]         # (B, 2*lstm_hidden)
        last = self.dropout(last)
        logits = self.classifier(last)
        return logits
