import json
import os
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch

from src.models.landmark_lstm import LandmarkBiLSTMClassifier

try:
    from mediapipe import solutions as mp_solutions
except (ImportError, AttributeError):
    from mediapipe.python import solutions as mp_solutions


POSE_POINTS = [
    ("nose", 0),
    ("rightEye", 5),
    ("leftEye", 2),
    ("rightEar", 8),
    ("leftEar", 7),
    ("rightShoulder", 12),
    ("leftShoulder", 11),
    ("rightElbow", 14),
    ("leftElbow", 13),
    ("rightWrist", 16),
    ("leftWrist", 15),
]

HAND_ORDER = [
    ("middleMCP", 9),
    ("middleDIP", 11),
    ("middlePIP", 10),
    ("middleTIP", 12),
    ("ringMCP", 13),
    ("ringDIP", 15),
    ("ringPIP", 14),
    ("ringTIP", 16),
    ("thumbCMC", 1),
    ("thumbMP", 2),
    ("thumbTIP", 4),
    ("thumbIP", 3),
    ("littleMCP", 17),
    ("littleDIP", 19),
    ("littlePIP", 18),
    ("littleTIP", 20),
    ("indexMCP", 5),
    ("indexDIP", 7),
    ("indexPIP", 6),
    ("indexTIP", 8),
    ("wrist", 0),
]


def _uniform_sample_indices(n: int, t: int) -> List[int]:
    if n <= 0:
        return [0] * t
    if n >= t:
        return np.linspace(0, n - 1, t).round().astype(int).tolist()
    indices = list(range(n))
    indices += [n - 1] * (t - n)
    return indices


class KArSLMediaPipeInference:
    """
    Inference adapter for the KArSL MediaPipe CSV model.

    It extracts the same 108-value frame representation used by the downloaded
    MediaPipe Pose CSV dataset: 12 body/neck keypoints + 21 right hand
    keypoints + 21 left hand keypoints, each with x/y coordinates.
    """

    def __init__(
        self,
        model_path: str,
        label_map_path: str = "./outputs/index/label2text.json",
        device: Optional[str] = None,
        num_frames: int = 64,
        input_dim: Optional[int] = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.num_frames = num_frames
        self.label2text = self._load_label_map(label_map_path)

        checkpoint = self._load_checkpoint(model_path)
        ckpt_args = checkpoint.get("args", {}) if isinstance(checkpoint, dict) else {}
        self.input_dim = int(input_dim or checkpoint.get("input_dim") or ckpt_args.get("input_dim") or 108)

        self.model = LandmarkBiLSTMClassifier(
            input_dim=self.input_dim,
            num_classes=502,
            hidden_size=int(ckpt_args.get("hidden_size", 256)),
            lstm_layers=int(ckpt_args.get("lstm_layers", 2)),
            dropout=float(ckpt_args.get("dropout", 0.3)),
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.mp_holistic = mp_solutions.holistic

    def _load_checkpoint(self, model_path: str):
        try:
            return torch.load(model_path, map_location=self.device, weights_only=False)
        except TypeError:
            return torch.load(model_path, map_location=self.device)

    def _load_label_map(self, label_map_path: str) -> Dict[str, str]:
        if os.path.isfile(label_map_path):
            with open(label_map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {str(i): f"Sign {i}" for i in range(1, 503)}

    def _point_xy(self, landmarks, idx: int) -> List[float]:
        if landmarks is None or len(landmarks.landmark) <= idx:
            return [0.0, 0.0]
        lm = landmarks.landmark[idx]
        return [float(lm.x), float(lm.y)]

    def _neck_xy(self, pose_landmarks) -> List[float]:
        if pose_landmarks is None:
            return [0.0, 0.0]
        right = self._point_xy(pose_landmarks, 12)
        left = self._point_xy(pose_landmarks, 11)
        if right == [0.0, 0.0] and left == [0.0, 0.0]:
            return [0.0, 0.0]
        return [(right[0] + left[0]) / 2.0, (right[1] + left[1]) / 2.0]

    def _frame_to_features(self, result) -> np.ndarray:
        values: List[float] = []
        pose = result.pose_landmarks

        for _, idx in POSE_POINTS:
            values.extend(self._point_xy(pose, idx))
        values.extend(self._neck_xy(pose))

        for _, idx in HAND_ORDER:
            values.extend(self._point_xy(result.right_hand_landmarks, idx))
        for _, idx in HAND_ORDER:
            values.extend(self._point_xy(result.left_hand_landmarks, idx))

        arr = np.asarray(values, dtype=np.float32)
        if arr.shape[0] != self.input_dim:
            fixed = np.zeros((self.input_dim,), dtype=np.float32)
            fixed[: min(self.input_dim, arr.shape[0])] = arr[: self.input_dim]
            arr = fixed
        return arr

    def _features_from_bgr_frames(self, frames: List[np.ndarray]) -> np.ndarray:
        if not frames:
            raise ValueError("No frames provided")

        features = []
        with self.mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            refine_face_landmarks=False,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.4,
        ) as holistic:
            for frame in frames:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = holistic.process(rgb)
                features.append(self._frame_to_features(result))

        arr = np.stack(features, axis=0)
        indices = _uniform_sample_indices(arr.shape[0], self.num_frames)
        sampled = arr[indices]
        mean = sampled.mean(axis=0, keepdims=True)
        std = sampled.std(axis=0, keepdims=True)
        sampled = (sampled - mean) / np.maximum(std, 1e-6)
        return sampled.astype(np.float32)

    def preprocess_video(self, video_path: str) -> torch.Tensor:
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        cap.release()
        if not frames:
            raise ValueError(f"No frames found in video: {video_path}")
        features = self._features_from_bgr_frames(frames)
        return torch.from_numpy(features).unsqueeze(0).float()

    def preprocess_frames(self, frames: List[np.ndarray]) -> torch.Tensor:
        features = self._features_from_bgr_frames(frames)
        return torch.from_numpy(features).unsqueeze(0).float()

    @torch.no_grad()
    def predict(self, tensor: torch.Tensor, top_k: int = 5) -> Dict:
        tensor = tensor.to(self.device)
        logits = self.model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        top_probs, top_indices = torch.topk(probs, k=min(top_k, probs.numel()))

        predictions = []
        for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
            label_id = str(int(idx) + 1)
            predictions.append(
                {
                    "label_id": label_id,
                    "text": self.label2text.get(label_id, f"Sign {label_id}"),
                    "confidence": float(prob),
                }
            )

        return {
            "top_prediction": predictions[0] if predictions else None,
            "top_k_predictions": predictions,
            "model": "karsl_mediapipe",
        }

    def predict_video(self, video_path: str, top_k: int = 5) -> Dict:
        return self.predict(self.preprocess_video(video_path), top_k=top_k)

    def predict_frames(self, frames: List[np.ndarray], top_k: int = 5) -> Dict:
        return self.predict(self.preprocess_frames(frames), top_k=top_k)
