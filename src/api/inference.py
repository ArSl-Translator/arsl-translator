import os
import json
import cv2
import numpy as np
from typing import List, Dict, Tuple
import torch
from pathlib import Path

from src.models.baseline_resnet_lstm import ResNetLSTMClassifier


class ModelInference:
    """Handles model loading and inference for ArSL sign language recognition."""

    def __init__(
        self,
        model_path: str,
        label_map_path: str = "./outputs/index/label2text.json",
        device: str = None,
        num_frames: int = 32,
        img_size: int = 224,
    ):
        """
        Args:
            model_path: Path to the trained model checkpoint (.pt file)
            label_map_path: Path to label2text.json mapping
            device: 'cuda' or 'cpu', auto-detect if None
            num_frames: Number of frames to sample from video
            img_size: Image size for model input
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.num_frames = num_frames
        self.img_size = img_size

        # ImageNet normalization (same as training)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        # Load label mapping
        with open(label_map_path, 'r', encoding='utf-8') as f:
            self.label2text = json.load(f)

        # Load model
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path: str) -> torch.nn.Module:
        """Load the trained model from checkpoint."""
        try:
            checkpoint = torch.load(
                model_path, map_location=self.device, weights_only=False
            )
        except TypeError:
            checkpoint = torch.load(model_path, map_location=self.device)

        # Create model instance
        model = ResNetLSTMClassifier(num_classes=502, backbone="resnet18", pretrained=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(self.device)

        return model

    def _uniform_sample_indices(self, n: int, t: int) -> List[int]:
        """Sample t indices uniformly from n frames."""
        if n <= 0:
            return [0] * t
        if n >= t:
            return np.linspace(0, n - 1, t).round().astype(int).tolist()
        # Pad by repeating last index
        idx = list(range(n))
        idx += [n - 1] * (t - n)
        return idx

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess a single frame (BGR format from cv2)."""
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Resize
        frame = cv2.resize(frame, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
        # Normalize to [0, 1]
        frame = frame.astype(np.float32) / 255.0
        # Apply ImageNet normalization
        frame = (frame - self.mean) / self.std
        return frame  # (H, W, 3)

    def preprocess_video(self, video_path: str) -> torch.Tensor:
        """
        Load and preprocess a video file.

        Args:
            video_path: Path to video file

        Returns:
            Tensor of shape (1, T, 3, H, W) ready for model input
        """
        cap = cv2.VideoCapture(video_path)
        frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        cap.release()

        if len(frames) == 0:
            raise ValueError(f"No frames found in video: {video_path}")

        # Sample frames uniformly
        indices = self._uniform_sample_indices(len(frames), self.num_frames)
        sampled_frames = [frames[i] for i in indices]

        # Preprocess each frame
        processed = [self._preprocess_frame(f) for f in sampled_frames]

        # Stack and transpose: (T, H, W, 3) -> (T, 3, H, W)
        arr = np.stack(processed, axis=0)
        arr = np.transpose(arr, (0, 3, 1, 2))

        # Convert to tensor and add batch dimension
        tensor = torch.from_numpy(arr).float().unsqueeze(0)  # (1, T, 3, H, W)

        return tensor

    def preprocess_frames(self, frames: List[np.ndarray]) -> torch.Tensor:
        """
        Preprocess a list of frames (for webcam or frame sequences).

        Args:
            frames: List of frames in BGR format (from cv2)

        Returns:
            Tensor of shape (1, T, 3, H, W) ready for model input
        """
        if len(frames) == 0:
            raise ValueError("No frames provided")

        # Sample frames uniformly
        indices = self._uniform_sample_indices(len(frames), self.num_frames)
        sampled_frames = [frames[i] for i in indices]

        # Preprocess each frame
        processed = [self._preprocess_frame(f) for f in sampled_frames]

        # Stack and transpose
        arr = np.stack(processed, axis=0)
        arr = np.transpose(arr, (0, 3, 1, 2))

        # Convert to tensor and add batch dimension
        tensor = torch.from_numpy(arr).float().unsqueeze(0)

        return tensor

    @torch.no_grad()
    def predict(self, video_tensor: torch.Tensor, top_k: int = 5) -> Dict:
        """
        Run inference on preprocessed video tensor.

        Args:
            video_tensor: Preprocessed video tensor of shape (1, T, 3, H, W)
            top_k: Number of top predictions to return

        Returns:
            Dictionary with prediction results
        """
        video_tensor = video_tensor.to(self.device)

        # Forward pass
        logits = self.model(video_tensor)  # (1, num_classes)
        probs = torch.softmax(logits, dim=1)[0]  # (num_classes,)

        # Get top-k predictions
        top_probs, top_indices = torch.topk(probs, k=min(top_k, len(probs)))

        # Convert to label IDs (model outputs 0..501, labels are 1..502)
        predictions = []
        for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
            label_id = str(int(idx) + 1)  # Convert back to 1-indexed
            text = self.label2text.get(label_id, f"Unknown_{label_id}")
            predictions.append({
                "label_id": label_id,
                "text": text,
                "confidence": float(prob)
            })

        return {
            "top_prediction": predictions[0] if predictions else None,
            "top_k_predictions": predictions
        }

    def predict_video(self, video_path: str, top_k: int = 5) -> Dict:
        """
        End-to-end prediction from video file.

        Args:
            video_path: Path to video file
            top_k: Number of top predictions to return

        Returns:
            Dictionary with prediction results
        """
        video_tensor = self.preprocess_video(video_path)
        return self.predict(video_tensor, top_k=top_k)

    def predict_frames(self, frames: List[np.ndarray], top_k: int = 5) -> Dict:
        """
        End-to-end prediction from frame list.

        Args:
            frames: List of frames in BGR format
            top_k: Number of top predictions to return

        Returns:
            Dictionary with prediction results
        """
        video_tensor = self.preprocess_frames(frames)
        return self.predict(video_tensor, top_k=top_k)
