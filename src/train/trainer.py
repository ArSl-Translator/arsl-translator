import os
import time
import math
from dataclasses import dataclass
from typing import Dict, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.train.metrics import topk_accuracy


@dataclass
class TrainConfig:
    epochs: int = 10
    lr: float = 3e-4
    weight_decay: float = 1e-4
    batch_size: int = 8
    num_workers: int = 2
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    log_every: int = 50


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: str,
) -> Dict[str, float]:
    model.train()
    total_loss = 0.0
    total_top1 = 0.0
    total_top5 = 0.0
    n_batches = 0

    for x, y in tqdm(loader, desc="train", leave=False):
        x = x.to(device)
        y = y.to(device)

        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        total_top1 += topk_accuracy(logits, y, k=1)
        total_top5 += topk_accuracy(logits, y, k=5)
        n_batches += 1

    return {
        "loss": total_loss / max(n_batches, 1),
        "top1": total_top1 / max(n_batches, 1),
        "top5": total_top5 / max(n_batches, 1),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: str,
    desc: str = "eval",
) -> Dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_top1 = 0.0
    total_top5 = 0.0
    n_batches = 0

    for x, y in tqdm(loader, desc=desc, leave=False):
        x = x.to(device)
        y = y.to(device)

        logits = model(x)
        loss = criterion(logits, y)

        total_loss += loss.item()
        total_top1 += topk_accuracy(logits, y, k=1)
        total_top5 += topk_accuracy(logits, y, k=5)
        n_batches += 1

    return {
        "loss": total_loss / max(n_batches, 1),
        "top1": total_top1 / max(n_batches, 1),
        "top5": total_top5 / max(n_batches, 1),
    }
