"""
demo_live.py
============
Real-time Arabic Sign Language Recognition demo.
Compatible with mediapipe >= 0.10.30 (new Tasks API).

Run:
    # Live webcam
    python demo_live.py --model best_model.pt --source 0

    # Video file
    python demo_live.py --model best_model.pt --source myvideo.mp4

Controls:
    Q — quit
    S — save screenshot
    C — clear buffer and reset prediction

Requirements:
    pip install mediapipe opencv-contrib-python torch numpy
"""

from __future__ import annotations

import argparse
import collections
import math
import os
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

# We use the first 25 MediaPipe landmarks × 3 coords = 75 features
# This matches the model's input_size=75 exactly
NUM_LANDMARKS = 25
FEATURE_DIM   = NUM_LANDMARKS * 3   # = 75

WINDOW_FRAMES = 92    # matches training avg (92 frames per sample)
STEP_FRAMES   = 15    # run prediction every N frames
MIN_FRAMES    = 30    # minimum frames before first prediction

FONT   = cv2.FONT_HERSHEY_SIMPLEX
GREEN  = (0, 220, 0)
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
GOLD   = (0, 215, 255)
ORANGE = (0, 165, 255)
CYAN   = (255, 255, 0)

SPECIAL = {"<PAD>", "<SOS>", "<EOS>"}

# Skeleton connections (MediaPipe landmark index pairs) for drawing
CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 31),
    (24, 26), (26, 28), (28, 32),
    (0, 11),  (0, 12),
]


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL  (identical architecture to train_arabsign.py)
# ═══════════════════════════════════════════════════════════════════════════════

class Encoder(nn.Module):
    def __init__(self, feature_dim, hidden_size, num_layers, dropout):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers  = num_layers
        self.rnn = nn.GRU(
            feature_dim, hidden_size, num_layers,
            bidirectional=True, dropout=dropout, batch_first=True,
        )
        self.fc_hidden = nn.Linear(hidden_size * 2, hidden_size)

    def forward(self, x):
        enc_out, hidden = self.rnn(x)
        enc_out = enc_out[:, :, :self.hidden_size] + enc_out[:, :, self.hidden_size:]
        hidden  = hidden.view(self.num_layers, 2, hidden.shape[1], self.hidden_size)
        hidden  = torch.tanh(self.fc_hidden(
            torch.cat([hidden[:, 0], hidden[:, 1]], dim=2)
        ))
        return enc_out, hidden


class Attention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size * 2, hidden_size)
        self.v    = nn.Parameter(torch.rand(hidden_size))
        self.v.data.uniform_(-1 / math.sqrt(hidden_size), 1 / math.sqrt(hidden_size))

    def forward(self, hidden, enc_out):
        T = enc_out.size(1)
        h = hidden.unsqueeze(1).repeat(1, T, 1)
        e = F.relu(self.attn(torch.cat([h, enc_out], 2))).transpose(1, 2)
        v = self.v.unsqueeze(0).unsqueeze(0).repeat(hidden.size(0), 1, 1)
        return F.softmax(torch.bmm(v, e).squeeze(1), dim=1).unsqueeze(1)


class Decoder(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers, dropout):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.attention  = Attention(hidden_size)
        self.gru = nn.GRU(
            hidden_size + embed_size, hidden_size, num_layers, dropout=dropout
        )
        self.out     = nn.Linear(hidden_size * 2, vocab_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, token, enc_out, hidden):
        emb     = self.dropout(self.embedding(token)).unsqueeze(0)
        attn    = self.attention(hidden[-1], enc_out)
        context = attn.bmm(enc_out).permute(1, 0, 2)
        out, hidden = self.gru(torch.cat([emb, context], dim=2), hidden)
        pred    = self.out(torch.cat([out.squeeze(0), context.squeeze(0)], dim=1))
        return F.log_softmax(pred, dim=1), hidden, attn


class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder, vocab_size):
        super().__init__()
        self.encoder    = encoder
        self.decoder    = decoder
        self.vocab_size = vocab_size

    @torch.no_grad()
    def translate(self, x: torch.Tensor, sos_idx: int,
                  eos_idx: int, max_len: int = 20) -> list[int]:
        """Greedy decode. x: (T, 75)"""
        self.eval()
        x = x.unsqueeze(0)                          # (1, T, 75)
        enc_out, hidden = self.encoder(x)
        token  = torch.tensor([sos_idx], device=x.device)
        result = []
        for _ in range(max_len):
            out, hidden, _ = self.decoder(token, enc_out, hidden)
            token = out.argmax(1)
            idx   = token.item()
            if idx == eos_idx:
                break
            result.append(idx)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD MODEL
# ═══════════════════════════════════════════════════════════════════════════════

def load_model(model_path: str, device: torch.device):
    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    cfg  = ckpt["cfg"]

    encoder = Encoder(FEATURE_DIM, cfg["hidden_size"],
                      cfg["num_layers"], cfg["enc_dropout"])
    decoder = Decoder(ckpt["vocab_size"], cfg["decoder_embed"],
                      cfg["hidden_size"], cfg["num_layers"], cfg["dec_dropout"])
    model   = Seq2Seq(encoder, decoder, ckpt["vocab_size"]).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    c2i = ckpt["c2i"]
    i2c = {int(k): v for k, v in ckpt["i2c"].items()}

    print(f"[Model] Loaded  vocab={ckpt['vocab_size']}  "
          f"hidden={cfg['hidden_size']}  layers={cfg['num_layers']}")
    return model, c2i, i2c


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIAPIPE MODEL DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def download_pose_model(save_path: str = "pose_landmarker_full.task") -> str:
    if os.path.exists(save_path):
        print(f"[MediaPipe] Using cached model: {save_path}")
        return save_path
    print("[MediaPipe] Downloading pose landmarker model (~5MB)...")
    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_full/float16/latest/"
        "pose_landmarker_full.task"
    )
    urllib.request.urlretrieve(url, save_path)
    print(f"[MediaPipe] Saved to {save_path}")
    return save_path


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def landmarks_to_features(landmarks) -> np.ndarray | None:
    """
    Take the first 25 MediaPipe pose landmarks → float32 (75,).
    25 landmarks × 3 coords (x, y, z) = 75 features = model input_size.
    MediaPipe gives 33 landmarks total; we use the first 25.
    """
    if landmarks is None or len(landmarks) < NUM_LANDMARKS:
        return None
    features = []
    for lm in landmarks[:NUM_LANDMARKS]:
        features.extend([lm.x, lm.y, lm.z])
    return np.array(features, dtype=np.float32)  # (75,)


# ═══════════════════════════════════════════════════════════════════════════════
# DECODE
# ═══════════════════════════════════════════════════════════════════════════════

def decode_indices(indices: list[int], i2c: dict) -> str:
    return " ".join(
        i2c.get(i, "") for i in indices
        if i2c.get(i, "") and i2c.get(i, "") not in SPECIAL
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SKELETON DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def draw_skeleton(frame, landmarks):
    h, w = frame.shape[:2]
    for lm in landmarks:
        cx = int(lm.x * w)
        cy = int(lm.y * h)
        cv2.circle(frame, (cx, cy), 5, GREEN, -1)
    for a, b in CONNECTIONS:
        if a < len(landmarks) and b < len(landmarks):
            ax, ay = int(landmarks[a].x * w), int(landmarks[a].y * h)
            bx, by = int(landmarks[b].x * w), int(landmarks[b].y * h)
            cv2.line(frame, (ax, ay), (bx, by), CYAN, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# UI OVERLAY
# ═══════════════════════════════════════════════════════════════════════════════

def draw_overlay(frame, prediction: str, buf_size: int,
                 fps: float, body_detected: bool):
    h, w = frame.shape[:2]

    # ── Top bar ──────────────────────────────────────────────────────────
    bar = frame.copy()
    cv2.rectangle(bar, (0, 0), (w, 85), BLACK, -1)
    cv2.addWeighted(bar, 0.65, frame, 0.35, 0, frame)

    cv2.putText(frame, "Arabic Sign Language Recognition",
                (10, 28), FONT, 0.75, GOLD, 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 100, 28), FONT, 0.55, WHITE, 1)

    # Body status indicator
    dot_col = GREEN if body_detected else (0, 0, 255)
    cv2.circle(frame, (w - 115, 22), 7, dot_col, -1)
    status = "Detected" if body_detected else "No body"
    cv2.putText(frame, status, (w - 105, 28), FONT, 0.4,
                dot_col, 1)

    # ── Buffer progress bar ───────────────────────────────────────────────
    pct   = min(buf_size / WINDOW_FRAMES, 1.0)
    bar_w = int(pct * (w - 20))
    cv2.rectangle(frame, (10, 50), (w - 10, 72), (40, 40, 40), -1)
    bar_col = GREEN if buf_size >= MIN_FRAMES else ORANGE
    if bar_w > 0:
        cv2.rectangle(frame, (10, 50), (10 + bar_w, 72), bar_col, -1)
    cv2.putText(frame, f"Buffer: {buf_size}/{WINDOW_FRAMES}  "
                f"({'ready' if buf_size >= MIN_FRAMES else 'collecting...'})",
                (15, 68), FONT, 0.42, WHITE, 1)

    # ── Bottom prediction box ─────────────────────────────────────────────
    bot = frame.copy()
    cv2.rectangle(bot, (0, h - 95), (w, h), BLACK, -1)
    cv2.addWeighted(bot, 0.72, frame, 0.28, 0, frame)

    cv2.putText(frame, "Predicted sentence:",
                (10, h - 65), FONT, 0.55, WHITE, 1)

    display = prediction if prediction else "(collecting frames...)"
    color   = GREEN if prediction else (120, 120, 120)
    (tw, _), _ = cv2.getTextSize(display, FONT, 1.0, 2)
    tx = max(10, (w - tw) // 2)
    cv2.putText(frame, display, (tx, h - 22), FONT, 1.0, color, 2)

    cv2.putText(frame, "Q=quit   S=screenshot   C=clear buffer",
                (10, h - 4), FONT, 0.38, (150, 150, 150), 1)

    return frame


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DEMO LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def run_demo(model_path: str, source, device: torch.device):

    # Load model and vocab
    model, c2i, i2c = load_model(model_path, device)
    sos_idx = c2i["<SOS>"]
    eos_idx = c2i["<EOS>"]

    # Download MediaPipe task model if needed
    task_path = download_pose_model()

    # Open video source
    if isinstance(source, str) and not source.isdigit() and os.path.exists(source):
        cap     = cv2.VideoCapture(source)
        is_file = True
        print(f"[Demo] Video file: {source}")
    else:
        cam_idx = int(source) if isinstance(source, str) else source
        cap     = cv2.VideoCapture(cam_idx)
        is_file = False
        print(f"[Demo] Webcam index: {cam_idx}")

    if not cap.isOpened():
        print("[ERROR] Could not open source.")
        print("  Webcam: try --source 1 or --source 2")
        print("  Video:  check the file path is correct")
        return

    # State
    frame_buffer    = collections.deque(maxlen=WINDOW_FRAMES)
    prediction      = ""
    frame_count     = 0
    last_pred_frame = 0
    fps             = 0.0
    fps_t0          = time.time()

    print(f"\n[Demo] Started.")
    print(f"  Feature dim  : {FEATURE_DIM}  (25 landmarks × 3 coords)")
    print(f"  Window       : {WINDOW_FRAMES} frames")
    print(f"  Predict every: {STEP_FRAMES} frames")
    print(f"  Min frames   : {MIN_FRAMES}\n")
    print("  Q — quit   S — screenshot   C — clear buffer\n")

    # Create MediaPipe landmarker (new Tasks API — no mp.solutions)
    options = PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=task_path),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )

    with PoseLandmarker.create_from_options(options) as landmarker:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if is_file:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            frame_count += 1

            # FPS counter
            if frame_count % 30 == 0:
                elapsed = time.time() - fps_t0
                fps     = 30 / max(elapsed, 1e-6)
                fps_t0  = time.time()

            # Run MediaPipe pose detection
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_img)

            body_detected = False
            feat          = None

            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                body_detected = True
                landmarks     = result.pose_landmarks[0]  # first person

                # Draw skeleton
                draw_skeleton(frame, landmarks)

                # Extract 75 features from first 25 landmarks
                feat = landmarks_to_features(landmarks)
                if feat is not None:
                    frame_buffer.append(feat)

            # Run model when buffer has enough frames
            buf_size = len(frame_buffer)
            if (buf_size >= MIN_FRAMES and
                    frame_count - last_pred_frame >= STEP_FRAMES):
                last_pred_frame = frame_count

                seq        = np.stack(list(frame_buffer), axis=0)  # (T, 75)
                x          = torch.tensor(seq, dtype=torch.float32).to(device)
                indices    = model.translate(x, sos_idx, eos_idx, max_len=20)
                prediction = decode_indices(indices, i2c)

            # Draw UI overlay
            frame = draw_overlay(frame, prediction, buf_size, fps, body_detected)

            cv2.imshow("Arabic Sign Language Recognition", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("[Demo] Quit.")
                break
            elif key == ord("s"):
                fname = f"screenshot_{frame_count}.jpg"
                cv2.imwrite(fname, frame)
                print(f"[Demo] Screenshot saved: {fname}")
            elif key == ord("c"):
                frame_buffer.clear()
                prediction = ""
                print("[Demo] Buffer cleared — prediction reset.")

    cap.release()
    cv2.destroyAllWindows()
    print("[Demo] Done.")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Real-time Arabic Sign Language Recognition"
    )
    p.add_argument("--model",  required=True,
                   help="Path to best_model.pt")
    p.add_argument("--source", default="0",
                   help="0 for webcam, or path to a video file")
    p.add_argument("--device", default="cpu",
                   help="cpu or cuda  (cpu is fine for demo)")
    return p.parse_args()


if __name__ == "__main__":
    args   = parse_args()
    device = torch.device(args.device)
    print(f"\n[Demo] device={device}  model={args.model}  source={args.source}\n")
    run_demo(model_path=args.model, source=args.source, device=device)
