from __future__ import annotations

import os
from typing import List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


def uniform_sample_indices(n: int, t: int) -> List[int]:
    if n <= 0:
        return [0] * t
    if n >= t:
        return np.linspace(0, n - 1, t).round().astype(int).tolist()
    indices = list(range(n))
    indices += [n - 1] * (t - n)
    return indices


class KArSLMediaPipeDataset(Dataset):
    """
    Reads a prepared manifest created by scripts/phase3_prepare_mediapipe_csv.py.
    Each manifest row points to one .npz sequence containing a float32 array named
    "features" with shape (T, F).
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        num_frames: int = 64,
        normalize: bool = True,
    ):
        self.df = manifest_df.reset_index(drop=True)
        self.num_frames = num_frames
        self.normalize = normalize

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        row = self.df.iloc[idx]
        npz_path = row["npz_path"]
        if not os.path.isfile(npz_path):
            raise FileNotFoundError(f"Prepared sequence not found: {npz_path}")

        with np.load(npz_path) as data:
            features = data["features"].astype(np.float32)

        if features.ndim != 2:
            raise ValueError(f"Expected (T, F) features in {npz_path}, got {features.shape}")

        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        indices = uniform_sample_indices(features.shape[0], self.num_frames)
        sampled = features[indices]

        if self.normalize:
            mean = sampled.mean(axis=0, keepdims=True)
            std = sampled.std(axis=0, keepdims=True)
            sampled = (sampled - mean) / np.maximum(std, 1e-6)

        x = torch.from_numpy(sampled).float()
        y = torch.tensor(int(row["label_id"]) - 1).long()
        return x, y
