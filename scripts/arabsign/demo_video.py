"""
demo_video.py
=============
Arabic Sign Language Recognition — Video File Demo.

Takes any .mp4 / .avi / .mov video file, runs MediaPipe pose detection on each
frame, feeds the skeleton into the trained model, and displays the Arabic
prediction overlaid on the actual video footage (not a stick figure).

Run:
    python demo_video.py --model best_model.pt --video myvideo.mp4

    # Save annotated output video instead of showing live:
    python demo_video.py --model best_model.pt --video myvideo.mp4 --save output.mp4

Controls (live mode):
    Q     — quit
    SPACE — pause / resume
    S     — save screenshot

Requirements:
    pip install mediapipe opencv-contrib-python torch numpy pillow arabic-reshaper python-bidi
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
from PIL import Image, ImageDraw, ImageFont

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

NUM_LANDMARKS = 25
FEATURE_DIM   = NUM_LANDMARKS * 3   # 75
WINDOW_FRAMES = 92
STEP_FRAMES   = 10
MIN_FRAMES    = 30

FONT_CV = cv2.FONT_HERSHEY_SIMPLEX
GREEN   = (0, 220, 0)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
GOLD    = (0, 215, 255)
CYAN    = (255, 255, 0)
ORANGE  = (0, 165, 255)

SPECIAL = {"<PAD>", "<SOS>", "<EOS>"}

CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 31),
    (24, 26), (26, 28), (28, 32),
    (0, 11),  (0, 12),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ARABIC TEXT
# ═══════════════════════════════════════════════════════════════════════════════

def _load_arabic_libs():
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return arabic_reshaper, get_display
    except ImportError:
        return None, None

arabic_reshaper_mod, bidi_display = _load_arabic_libs()


def prepare_arabic(text: str) -> str:
    if arabic_reshaper_mod and bidi_display:
        return bidi_display(arabic_reshaper_mod.reshape(text))
    return text


def draw_arabic_text(canvas: np.ndarray, text: str, x: int, y: int,
                     font_size: int = 38, color=(255, 255, 255)) -> np.ndarray:
    if not text:
        return canvas
    prepared = prepare_arabic(text)
    img_pil  = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw     = ImageDraw.Draw(img_pil)
    font     = None
    for fc in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf",
               "C:/Windows/Fonts/tahoma.ttf", "arial.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try:
            font = ImageFont.truetype(fc, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    pil_color = (color[2], color[1], color[0])
    draw.text((x, y), prepared, font=font, fill=pil_color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class Encoder(nn.Module):
    def __init__(self, feature_dim, hidden_size, num_layers, dropout):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers  = num_layers
        self.rnn = nn.GRU(feature_dim, hidden_size, num_layers,
                          bidirectional=True, dropout=dropout, batch_first=True)
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
        self.v.data.uniform_(-1/math.sqrt(hidden_size), 1/math.sqrt(hidden_size))

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
        self.gru = nn.GRU(hidden_size + embed_size, hidden_size,
                          num_layers, dropout=dropout)
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
    def translate(self, x, sos_idx, eos_idx, max_len=20):
        self.eval()
        x = x.unsqueeze(0)
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


def load_model(model_path, device):
    ckpt    = torch.load(model_path, map_location=device, weights_only=False)
    cfg     = ckpt["cfg"]
    encoder = Encoder(FEATURE_DIM, cfg["hidden_size"], cfg["num_layers"], cfg["enc_dropout"])
    decoder = Decoder(ckpt["vocab_size"], cfg["decoder_embed"], cfg["hidden_size"],
                      cfg["num_layers"], cfg["dec_dropout"])
    model   = Seq2Seq(encoder, decoder, ckpt["vocab_size"]).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    c2i = ckpt["c2i"]
    i2c = {int(k): v for k, v in ckpt["i2c"].items()}
    print(f"[Model] vocab={ckpt['vocab_size']}  hidden={cfg['hidden_size']}  layers={cfg['num_layers']}")
    return model, c2i, i2c


def decode_indices(indices, i2c):
    return " ".join(
        i2c.get(i, "") for i in indices
        if i2c.get(i, "") and i2c.get(i, "") not in SPECIAL
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIAPIPE
# ═══════════════════════════════════════════════════════════════════════════════

def download_pose_model(save_path="pose_landmarker_full.task"):
    if os.path.exists(save_path):
        return save_path
    print("[MediaPipe] Downloading pose model (~5MB)...")
    url = ("https://storage.googleapis.com/mediapipe-models/"
           "pose_landmarker/pose_landmarker_full/float16/latest/"
           "pose_landmarker_full.task")
    urllib.request.urlretrieve(url, save_path)
    print(f"[MediaPipe] Saved to {save_path}")
    return save_path


def landmarks_to_features(landmarks) -> np.ndarray | None:
    if landmarks is None or len(landmarks) < NUM_LANDMARKS:
        return None
    features = []
    for lm in landmarks[:NUM_LANDMARKS]:
        features.extend([lm.x, lm.y, lm.z])
    return np.array(features, dtype=np.float32)


def draw_skeleton_on_frame(frame, landmarks):
    h, w = frame.shape[:2]
    for lm in landmarks:
        cx = int(lm.x * w)
        cy = int(lm.y * h)
        cv2.circle(frame, (cx, cy), 5, GREEN, -1, cv2.LINE_AA)
    for a, b in CONNECTIONS:
        if a < len(landmarks) and b < len(landmarks):
            ax = int(landmarks[a].x * w)
            ay = int(landmarks[a].y * h)
            bx = int(landmarks[b].x * w)
            by = int(landmarks[b].y * h)
            cv2.line(frame, (ax, ay), (bx, by), CYAN, 2, cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════════════════════
# OVERLAY
# ═══════════════════════════════════════════════════════════════════════════════

def draw_overlay(frame, prediction, buf_size, fps, body_detected, frame_num, total):
    h, w = frame.shape[:2]

    # Top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 100), BLACK, -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    cv2.putText(frame, "Arabic Sign Language Recognition",
                (10, 30), FONT_CV, 0.8, GOLD, 2, cv2.LINE_AA)

    # FPS + frame counter
    info = f"FPS: {fps:.1f}   Frame: {frame_num}"
    if total:
        info += f"/{total}"
    cv2.putText(frame, info, (w - 260, 30), FONT_CV, 0.5, WHITE, 1)

    # Body detection dot
    dot_col = GREEN if body_detected else (0, 0, 255)
    cv2.circle(frame, (w - 275, 24), 7, dot_col, -1)

    # Buffer bar
    pct   = min(buf_size / WINDOW_FRAMES, 1.0)
    bar_w = int(pct * (w - 20))
    cv2.rectangle(frame, (10, 48), (w - 10, 65), (40, 40, 40), -1)
    bar_col = GREEN if buf_size >= MIN_FRAMES else ORANGE
    if bar_w > 0:
        cv2.rectangle(frame, (10, 48), (10 + bar_w, 65), bar_col, -1)
    status = "predicting" if buf_size >= MIN_FRAMES else "collecting..."
    cv2.putText(frame, f"Buffer: {buf_size}/{WINDOW_FRAMES}  ({status})",
                (15, 62), FONT_CV, 0.4, WHITE, 1)

    # Bottom prediction box
    bot = frame.copy()
    cv2.rectangle(bot, (0, h - 80), (w, h), BLACK, -1)
    cv2.addWeighted(bot, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame, "Prediction:",
                (10, h - 50), FONT_CV, 0.6, WHITE, 1, cv2.LINE_AA)

    pred_text  = prediction if prediction else "(collecting frames...)"
    pred_color = GREEN if prediction else (120, 120, 120)
    frame = draw_arabic_text(frame, pred_text,
                             x=150, y=h - 72,
                             font_size=40, color=pred_color)

    cv2.putText(frame, "Q=quit   SPACE=pause   S=screenshot",
                (10, h - 6), FONT_CV, 0.38, (150, 150, 150), 1)

    return frame


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_video_demo(model_path, video_path, save_path, device):

    model, c2i, i2c = load_model(model_path, device)
    sos_idx = c2i["<SOS>"]
    eos_idx = c2i["<EOS>"]

    task_path = download_pose_model()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_fps     = cap.get(cv2.CAP_PROP_FPS) or 30
    orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[Video] {video_path}")
    print(f"[Video] {orig_w}×{orig_h}  {orig_fps:.1f}fps  {total_frames} frames")

    # Output writer
    writer = None
    if save_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(save_path, fourcc, orig_fps, (orig_w, orig_h))
        print(f"[Video] Saving output to: {save_path}")

    frame_buffer    = collections.deque(maxlen=WINDOW_FRAMES)
    prediction      = ""
    frame_count     = 0
    last_pred_frame = -STEP_FRAMES
    fps             = 0.0
    fps_t0          = time.time()
    paused          = False

    print("\nControls: Q=quit   SPACE=pause   S=screenshot\n")

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
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("[Video] End of video.")
                    break
                frame_count += 1
            else:
                # Show last frame while paused
                key = cv2.waitKey(30) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord(" "):
                    paused = False
                    print("Resumed.")
                continue

            # FPS
            if frame_count % 30 == 0:
                elapsed = time.time() - fps_t0
                fps     = 30 / max(elapsed, 1e-6)
                fps_t0  = time.time()

            # MediaPipe
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_img)

            body_detected = False
            feat          = None

            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                body_detected = True
                landmarks     = result.pose_landmarks[0]
                draw_skeleton_on_frame(frame, landmarks)
                feat = landmarks_to_features(landmarks)
                if feat is not None:
                    frame_buffer.append(feat)

            # Predict
            buf_size = len(frame_buffer)
            if (buf_size >= MIN_FRAMES and
                    frame_count - last_pred_frame >= STEP_FRAMES):
                last_pred_frame = frame_count
                seq        = np.stack(list(frame_buffer), axis=0)
                x          = torch.tensor(seq, dtype=torch.float32).to(device)
                indices    = model.translate(x, sos_idx, eos_idx, max_len=20)
                prediction = decode_indices(indices, i2c)
                if prediction:
                    print(f"  Frame {frame_count:>4}/{total_frames} | pred: '{prediction}'")

            # Draw overlay on actual video frame
            frame = draw_overlay(frame, prediction, buf_size, fps,
                                 body_detected, frame_count, total_frames)

            # Show or save
            if writer:
                writer.write(frame)
                if frame_count % 60 == 0:
                    pct = frame_count / max(total_frames, 1) * 100
                    print(f"  Processing: {pct:.0f}%  ({frame_count}/{total_frames})")
            else:
                cv2.imshow("Arabic Sign Language Recognition — Video", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("Quit.")
                    break
                elif key == ord(" "):
                    paused = True
                    print("Paused. Press SPACE to resume.")
                elif key == ord("s"):
                    fname = f"screenshot_{frame_count}.jpg"
                    cv2.imwrite(fname, frame)
                    print(f"Saved {fname}")

    cap.release()
    if writer:
        writer.release()
        print(f"\n[Done] Saved to: {save_path}")
        print("Play it with any video player.")
    cv2.destroyAllWindows()
    print("[Done]")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Arabic Sign Language Recognition — Video Demo"
    )
    p.add_argument("--model", required=True,
                   help="Path to best_model.pt")
    p.add_argument("--video", required=True,
                   help="Path to input video file (.mp4 / .avi / .mov)")
    p.add_argument("--save",  default=None,
                   help="Optional: save annotated output to this path (e.g. output.mp4)")
    p.add_argument("--device", default="cpu")
    return p.parse_args()


if __name__ == "__main__":
    args   = parse_args()
    device = torch.device(args.device)
    print(f"\n[Demo] model={args.model}  video={args.video}\n")
    run_video_demo(
        model_path = args.model,
        video_path = args.video,
        save_path  = args.save,
        device     = device,
    )
