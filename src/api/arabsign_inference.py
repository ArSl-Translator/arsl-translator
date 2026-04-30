import base64
import math
import os
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import scipy.io as sio
import torch
import torch.nn as nn
import torch.nn.functional as F


FEATURE_DIM = 75
NUM_LANDMARKS = 25
MIN_FRAMES = 30
SPECIAL_TOKENS = {"<PAD>", "<SOS>", "<EOS>"}

MEDIAPIPE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
MEDIAPIPE_MODEL_PATH = os.getenv(
    "MEDIAPIPE_MODEL_PATH",
    "./mediapipe_models/pose_landmarker_full.task",
)


class Encoder(nn.Module):
    def __init__(self, feature_dim, hidden_size, num_layers, dropout):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.rnn = nn.GRU(
            feature_dim,
            hidden_size,
            num_layers,
            bidirectional=True,
            dropout=dropout,
            batch_first=True,
        )
        self.fc_hidden = nn.Linear(hidden_size * 2, hidden_size)

    def forward(self, x):
        enc_out, hidden = self.rnn(x)
        enc_out = enc_out[:, :, : self.hidden_size] + enc_out[:, :, self.hidden_size :]
        hidden = hidden.view(self.num_layers, 2, hidden.shape[1], self.hidden_size)
        hidden = torch.tanh(
            self.fc_hidden(torch.cat([hidden[:, 0], hidden[:, 1]], dim=2))
        )
        return enc_out, hidden


class Attention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size * 2, hidden_size)
        self.v = nn.Parameter(torch.rand(hidden_size))
        self.v.data.uniform_(-1 / math.sqrt(hidden_size), 1 / math.sqrt(hidden_size))

    def forward(self, hidden, enc_out):
        t = enc_out.size(1)
        h = hidden.unsqueeze(1).repeat(1, t, 1)
        e = F.relu(self.attn(torch.cat([h, enc_out], 2))).transpose(1, 2)
        v = self.v.unsqueeze(0).unsqueeze(0).repeat(hidden.size(0), 1, 1)
        return F.softmax(torch.bmm(v, e).squeeze(1), dim=1).unsqueeze(1)


class Decoder(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers, dropout):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.attention = Attention(hidden_size)
        self.gru = nn.GRU(hidden_size + embed_size, hidden_size, num_layers, dropout=dropout)
        self.out = nn.Linear(hidden_size * 2, vocab_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, token, enc_out, hidden):
        emb = self.dropout(self.embedding(token)).unsqueeze(0)
        attn = self.attention(hidden[-1], enc_out)
        context = attn.bmm(enc_out).permute(1, 0, 2)
        out, hidden = self.gru(torch.cat([emb, context], dim=2), hidden)
        pred = self.out(torch.cat([out.squeeze(0), context.squeeze(0)], dim=1))
        return F.log_softmax(pred, dim=1), hidden


class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder, vocab_size):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.vocab_size = vocab_size

    @torch.no_grad()
    def translate(self, x: torch.Tensor, sos_idx: int, eos_idx: int, max_len: int = 20):
        self.eval()
        x = x.unsqueeze(0)
        enc_out, hidden = self.encoder(x)
        token = torch.tensor([sos_idx], device=x.device)
        result = []
        for _ in range(max_len):
            out, hidden = self.decoder(token, enc_out, hidden)
            token = out.argmax(1)
            idx = token.item()
            if idx == eos_idx:
                break
            result.append(idx)
        return result


class ArabSignInference:
    """Inference adapter for the ArabSign GRU attention model."""

    def __init__(self, model_path: str, device: Optional[str] = None):
        self.model_path = model_path
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model, self.c2i, self.i2c = self._load_model(model_path)

    def _load_model(self, model_path: str):
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        cfg = checkpoint["cfg"]

        encoder = Encoder(
            FEATURE_DIM,
            cfg["hidden_size"],
            cfg["num_layers"],
            cfg["enc_dropout"],
        )
        decoder = Decoder(
            checkpoint["vocab_size"],
            cfg["decoder_embed"],
            cfg["hidden_size"],
            cfg["num_layers"],
            cfg["dec_dropout"],
        )
        model = Seq2Seq(encoder, decoder, checkpoint["vocab_size"]).to(self.device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()

        i2c = {int(k): v for k, v in checkpoint["i2c"].items()}
        return model, checkpoint["c2i"], i2c

    def predict_features(self, features: np.ndarray):
        if len(features) < MIN_FRAMES:
            raise ValueError(f"Need at least {MIN_FRAMES} detected pose frames, got {len(features)}")

        x = torch.tensor(features, dtype=torch.float32).to(self.device)
        indices = self.model.translate(x, self.c2i["<SOS>"], self.c2i["<EOS>"], max_len=20)
        text = " ".join(
            self.i2c.get(i, "")
            for i in indices
            if self.i2c.get(i, "") and self.i2c.get(i, "") not in SPECIAL_TOKENS
        )

        return {
            "top_prediction": {
                "label_id": "arabsign",
                "text": text or "No translation",
                "confidence": 1.0,
            },
            "top_k_predictions": [
                {
                    "label_id": "arabsign",
                    "text": text or "No translation",
                    "confidence": 1.0,
                }
            ],
            "model": "arabsign",
            "num_pose_frames": int(len(features)),
        }

    def predict_video(self, video_path: str, top_k: int = 1):
        return self.predict_features(extract_from_video(video_path))

    def predict_frames(self, frames: List[np.ndarray], top_k: int = 1):
        return self.predict_features(extract_from_frames(frames))

    def predict_mat(self, mat_path: str):
        return self.predict_features(extract_from_mat(mat_path))

    def predict_npy(self, npy_path: str):
        return self.predict_features(extract_from_npy(npy_path))


def mediapipe_model_available() -> bool:
    return Path(MEDIAPIPE_MODEL_PATH).is_file()


def _get_landmarker():
    if not mediapipe_model_available():
        raise FileNotFoundError(
            f"MediaPipe pose model not found at {MEDIAPIPE_MODEL_PATH}. "
            f"Download it from {MEDIAPIPE_MODEL_URL}"
        )

    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
        VisionTaskRunningMode,
    )

    options = mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MEDIAPIPE_MODEL_PATH),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )
    return mp_vision.PoseLandmarker.create_from_options(options)


def extract_from_video(video_path: str) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    features = []
    with _get_landmarker() as landmarker:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            feature = _extract_frame_feature(landmarker, frame)
            if feature is not None:
                features.append(feature)

    cap.release()
    if not features:
        raise ValueError("No body detected in video")
    return np.stack(features, axis=0)


def extract_from_frames(frames: List[np.ndarray]) -> np.ndarray:
    features = []
    with _get_landmarker() as landmarker:
        for frame in frames:
            feature = _extract_frame_feature(landmarker, frame)
            if feature is not None:
                features.append(feature)

    if not features:
        raise ValueError("No body detected in webcam frames")
    return np.stack(features, axis=0)


def extract_from_mat(mat_path: str) -> np.ndarray:
    mat = sio.loadmat(mat_path)
    body = mat.get("body")
    if body is None:
        raise ValueError("No 'body' key in MAT file")

    body_flat = body.flatten()
    features = np.empty((len(body_flat), FEATURE_DIM), dtype=np.float32)
    for i, item in enumerate(body_flat):
        pos = item["Position"]
        features[i] = np.array(pos, dtype=np.float32).T.flatten()
    return features


def extract_from_npy(npy_path: str) -> np.ndarray:
    arr = np.load(npy_path).astype(np.float32)
    if arr.ndim != 2 or arr.shape[1] != FEATURE_DIM:
        raise ValueError(f"Expected (T, {FEATURE_DIM}), got {arr.shape}")
    return arr


def decode_base64_frame(frame_b64: str) -> np.ndarray:
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    raw = base64.b64decode(frame_b64.strip())
    nparr = np.frombuffer(raw, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("OpenCV failed to decode frame")
    return frame


def _extract_frame_feature(landmarker, frame: np.ndarray) -> Optional[np.ndarray]:
    import mediapipe as mp

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_img)
    if not result.pose_landmarks:
        return None
    return _landmarks_to_features(result.pose_landmarks[0])


def _landmarks_to_features(landmarks) -> Optional[np.ndarray]:
    if landmarks is None or len(landmarks) < NUM_LANDMARKS:
        return None

    features = []
    for lm in landmarks[:NUM_LANDMARKS]:
        features.extend([lm.x, lm.y, lm.z])
    return np.array(features, dtype=np.float32)
