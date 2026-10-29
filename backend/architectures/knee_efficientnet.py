import torch
import torch.nn as nn
from torchvision.models import efficientnet_b5

class EfficientNetB5_Knee(nn.Module):
    """
    CleanLab-optimized EfficientNet-B5 for Kellgren-Lawrence Knee Osteoarthritis grading (5 classes)
    Reproduced exactly from knee-osteoarthritis-notebook.ipynb
    """
    def __init__(self, num_classes=5):
        super().__init__()
        self.backbone = efficientnet_b5(weights=None)
        in_features = self.backbone.classifier[1].in_features  # 2048
        self.backbone.classifier = nn.Identity()

        self.dropout1 = nn.Dropout(0.50)
        self.fc = nn.Linear(in_features, 256)
        self.bn = nn.BatchNorm1d(256)
        self.relu = nn.ReLU(inplace=True)
        self.dropout2 = nn.Dropout(0.40)
        self.out = nn.Linear(256, num_classes)

    def forward_features(self, x):
        x = self.backbone.features(x)
        x = self.backbone.avgpool(x)
        x = torch.flatten(x, 1)
        return x

    def forward(self, x):
        x = self.forward_features(x)
        embedding = self.dropout1(x)
        x = self.fc(embedding)
        x = self.bn(x)
        x = self.relu(x)
        x = self.dropout2(x)
        logits = self.out(x)
        return logits
