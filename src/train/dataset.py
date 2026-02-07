import os
import cv2
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional

import torch
from torch.utils.data import Dataset


def _is_img(name: str) -> bool:
    n = name.lower()
    return n.endswith(".jpg") or n.endswith(".jpeg") or n.endswith(".png")


def _sorted_frame_paths(frames_dir: str) -> List[str]:
    files = [f for f in os.listdir(frames_dir) if _is_img(f)]
    files.sort()
    return [os.path.join(frames_dir, f) for f in files]


def _uniform_sample_indices(n: int, t: int) -> List[int]:
    """
    Returns t indices sampled uniformly from [0..n-1].
    If n < t, pads by repeating last index.
    """
    if n <= 0:
        return [0] * t
    if n >= t:
        return np.linspace(0, n - 1, t).round().astype(int).tolist()
    # pad
    idx = list(range(n))
    idx += [n - 1] * (t - n)
    return idx


class KArSLFramesDataset(Dataset):
    """
    Reads samples from data_index.csv.
    Each row corresponds to one sample folder containing frames.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        num_frames: int = 32,
        img_size: int = 224,
        normalize: bool = True,
    ):
        self.df = df.reset_index(drop=True)
        self.num_frames = num_frames
        self.img_size = img_size
        self.normalize = normalize

        # ImageNet normalization (works well with ResNet pretrained)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __len__(self) -> int:
        return len(self.df)

    def _load_frame(self, path: str) -> np.ndarray:
        img = cv2.imread(path)  # BGR
        if img is None:
            # fallback: blank image if corrupted/missing
            img = np.zeros((self.img_size, self.img_size, 3), dtype=np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
        img = img.astype(np.float32) / 255.0
        if self.normalize:
            img = (img - self.mean) / self.std
        return img  # (H, W, 3)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        row = self.df.iloc[idx]
        frames_dir = row["frames_dir"]
        label_id = int(row["label_id"])  # 1..502

        paths = _sorted_frame_paths(frames_dir)
        n = len(paths)
        indices = _uniform_sample_indices(n, self.num_frames)

        frames = []
        for i in indices:
            p = paths[i] if n > 0 else ""
            frame = self._load_frame(p) if n > 0 else np.zeros((self.img_size, self.img_size, 3), dtype=np.float32)
            frames.append(frame)

        arr = np.stack(frames, axis=0)            # (T, H, W, 3)
        arr = np.transpose(arr, (0, 3, 1, 2))     # (T, 3, H, W)
        x = torch.from_numpy(arr).float()         # float32

        y = torch.tensor(label_id - 1).long()     # convert to 0..501
        return x, y
