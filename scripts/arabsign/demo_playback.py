"""
demo_playback.py
================
Presentation demo — animates a saved .npy skeleton sample through the model.
Fixes:
  - Arabic text rendered correctly using PIL (not OpenCV)
  - Skeleton normalized per-frame relative to hip center so it stays stable

Run:
    python demo_playback.py --model best_model.pt --sample test_sample.npy --label test_sample_label.txt

Requirements:
    pip install opencv-contrib-python torch numpy pillow arabic-reshaper python-bidi
"""

from __future__ import annotations

import argparse
import math
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_DIM   = 75
CANVAS_W      = 960
CANVAS_H      = 680
PLAYBACK_FPS  = 12
MIN_FRAMES    = 30
STEP_FRAMES   = 10

FONT_CV = cv2.FONT_HERSHEY_SIMPLEX
GREEN   = (0, 220, 0)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
GOLD    = (0, 215, 255)
CYAN    = (255, 255, 0)
ORANGE  = (0, 165, 255)

SPECIAL = {"<PAD>", "<SOS>", "<EOS>"}

# Connections between the 25 joints we use
CONNECTIONS = [
    (0, 11), (0, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (15, 17), (15, 19), (15, 21),
    (16, 18), (16, 20), (16, 22),
    (11, 23), (12, 24),
    (23, 24),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ARABIC TEXT RENDERING  (PIL — supports RTL Arabic correctly on Windows)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_arabic_libs():
    """Try to import arabic_reshaper and bidi. Return True if available."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return arabic_reshaper, get_display
    except ImportError:
        return None, None


arabic_reshaper_mod, bidi_display = _load_arabic_libs()


def prepare_arabic(text: str) -> str:
    """Shape and reorder Arabic text for correct display."""
    if arabic_reshaper_mod and bidi_display:
        reshaped = arabic_reshaper_mod.reshape(text)
        return bidi_display(reshaped)
    return text   # fallback — may show as ???


def draw_arabic_text(canvas: np.ndarray, text: str, x: int, y: int,
                     font_size: int = 36, color=(255, 255, 255)) -> np.ndarray:
    """
    Draw Arabic text on an OpenCV canvas using PIL.
    Returns the modified canvas.
    """
    if not text:
        return canvas

    prepared = prepare_arabic(text)

    # Convert canvas to PIL
    img_pil = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw    = ImageDraw.Draw(img_pil)

    # Try to load a system font that supports Arabic
    font = None
    font_candidates = [
        "arial.ttf", "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fc in font_candidates:
        try:
            font = ImageFont.truetype(fc, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # PIL color is RGB
    pil_color = (color[2], color[1], color[0])
    draw.text((x, y), prepared, font=font, fill=pil_color)

    # Convert back to OpenCV BGR
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL
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
# SKELETON NORMALISATION  — stable body-centred coordinates
# ═══════════════════════════════════════════════════════════════════════════════

def normalise_frame(feat: np.ndarray) -> np.ndarray:
    """
    Normalise one frame so the skeleton is centred and scaled consistently.
    feat: (75,) — 25 joints × (x, y, z)

    Steps:
      1. Centre on hip midpoint (joints 23 and 24 in MediaPipe, indices 0 and 1
         in our 25-joint list — but in Kinect order joints 23,24 are indices 0,1
         of x/y/z interleaved as feat[0*3], feat[1*3] for x of joint 0,1)
      2. Scale by shoulder width so size is consistent across frames
    """
    joints_x = feat[0::3].copy()   # shape (25,)
    joints_y = feat[1::3].copy()   # shape (25,)

    # Hip centre = average of joint 23 and 24
    # In our 25-joint extraction (landmarks[:25]):
    # joint 23 = index 23, joint 24 = index 24
    hip_x = (joints_x[23] + joints_x[24]) / 2
    hip_y = (joints_y[23] + joints_y[24]) / 2

    joints_x -= hip_x
    joints_y -= hip_y

    # Scale by shoulder width (joints 11 and 12)
    shoulder_w = abs(joints_x[11] - joints_x[12])
    if shoulder_w < 1e-6:
        shoulder_w = 1.0
    scale = 1.0 / shoulder_w

    joints_x *= scale
    joints_y *= scale

    out = feat.copy()
    out[0::3] = joints_x
    out[1::3] = joints_y
    return out


def frame_to_pixels(feat: np.ndarray) -> list[tuple[int, int]]:
    """
    Convert normalised frame features to pixel coordinates on canvas.
    Body centre → canvas centre. Scale to fit nicely.
    """
    cx = CANVAS_W // 2
    cy = int(CANVAS_H * 0.42)   # slightly above centre (head at top)
    scale = 120                  # pixels per unit shoulder-width

    joints = []
    for i in range(25):
        x = feat[i * 3]
        y = feat[i * 3 + 1]
        px = int(cx + x * scale)
        py = int(cy + y * scale)
        joints.append((px, py))
    return joints


def preprocess_frames(frames: np.ndarray) -> np.ndarray:
    """Normalise all frames for display."""
    return np.array([normalise_frame(f) for f in frames])


# ═══════════════════════════════════════════════════════════════════════════════
# DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def draw_skeleton(canvas, joints):
    for a, b in CONNECTIONS:
        if a < len(joints) and b < len(joints):
            pa, pb = joints[a], joints[b]
            if (0 < pa[0] < CANVAS_W and 0 < pa[1] < CANVAS_H and
                    0 < pb[0] < CANVAS_W and 0 < pb[1] < CANVAS_H):
                cv2.line(canvas, pa, pb, CYAN, 3, cv2.LINE_AA)

    for i, (px, py) in enumerate(joints):
        if not (0 < px < CANVAS_W and 0 < py < CANVAS_H):
            continue
        if i == 0:                       # head
            cv2.circle(canvas, (px, py), 18, WHITE, -1, cv2.LINE_AA)
            cv2.circle(canvas, (px, py), 18, CYAN, 2, cv2.LINE_AA)
        elif i in (11, 12):              # shoulders
            cv2.circle(canvas, (px, py), 9, GOLD, -1, cv2.LINE_AA)
        elif i in (15, 16):              # wrists
            cv2.circle(canvas, (px, py), 9, ORANGE, -1, cv2.LINE_AA)
        elif i in (23, 24):              # hips
            cv2.circle(canvas, (px, py), 7, (200, 100, 255), -1, cv2.LINE_AA)
        else:
            cv2.circle(canvas, (px, py), 5, GREEN, -1, cv2.LINE_AA)


def draw_ui(canvas, frame_idx, total_frames, buf_size,
            ground_truth, prediction, correct, paused):
    h, w = canvas.shape[:2]

    # ── Top bar ──────────────────────────────────────────────────────────
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, 155), BLACK, -1)
    cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)

    cv2.putText(canvas, "Arabic Sign Language Recognition — Demo",
                (10, 32), FONT_CV, 0.85, GOLD, 2, cv2.LINE_AA)
    cv2.putText(canvas, "Model: Bidirectional GRU + Bahdanau Attention  |  "
                "Test WER: 0.26%   BLEU-1: 0.997",
                (10, 58), FONT_CV, 0.48, GREEN, 1, cv2.LINE_AA)

    # Frame progress
    pct   = (frame_idx + 1) / max(total_frames, 1)
    bar_w = int(pct * (w - 20))
    cv2.rectangle(canvas, (10, 72), (w - 10, 90), (40, 40, 40), -1)
    cv2.rectangle(canvas, (10, 72), (10 + bar_w, 90), CYAN, -1)
    cv2.putText(canvas, f"Frame {frame_idx + 1}/{total_frames}",
                (15, 88), FONT_CV, 0.42, WHITE, 1)

    # Buffer
    bpct   = min(buf_size / total_frames, 1.0)
    bbar_w = int(bpct * (w - 20))
    cv2.rectangle(canvas, (10, 98), (w - 10, 116), (40, 40, 40), -1)
    buf_col = GREEN if buf_size >= MIN_FRAMES else ORANGE
    if bbar_w > 0:
        cv2.rectangle(canvas, (10, 98), (10 + bbar_w, 116), buf_col, -1)
    status = "predicting" if buf_size >= MIN_FRAMES else "collecting..."
    cv2.putText(canvas, f"Buffer: {buf_size}/{total_frames}  ({status})",
                (15, 113), FONT_CV, 0.42, WHITE, 1)

    if paused:
        cv2.putText(canvas, "|| PAUSED", (w - 160, 88),
                    FONT_CV, 0.6, ORANGE, 2, cv2.LINE_AA)

    # ── Bottom box ────────────────────────────────────────────────────────
    bot = canvas.copy()
    cv2.rectangle(bot, (0, h - 160), (w, h), BLACK, -1)
    cv2.addWeighted(bot, 0.78, canvas, 0.22, 0, canvas)

    # Ground truth label (Arabic)
    cv2.putText(canvas, "Ground truth:", (10, h - 120),
                FONT_CV, 0.6, WHITE, 1, cv2.LINE_AA)
    canvas = draw_arabic_text(canvas, ground_truth,
                              x=220, y=h - 140, font_size=42,
                              color=(255, 255, 255))

    # Prediction (Arabic)
    cv2.putText(canvas, "Model prediction:", (10, h - 65),
                FONT_CV, 0.6, WHITE, 1, cv2.LINE_AA)
    pred_text  = prediction if prediction else "(collecting frames...)"
    pred_color = GREEN if (prediction and correct) else (ORANGE if prediction else (120, 120, 120))
    canvas = draw_arabic_text(canvas, pred_text,
                              x=220, y=h - 85, font_size=42,
                              color=pred_color)

    # CORRECT / INCORRECT badge
    if prediction:
        if correct:
            cv2.putText(canvas, "CORRECT", (10, h - 18),
                        FONT_CV, 0.9, GREEN, 3, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "INCORRECT", (10, h - 18),
                        FONT_CV, 0.9, ORANGE, 3, cv2.LINE_AA)

    cv2.putText(canvas, "SPACE=pause   R=restart   Q=quit",
                (w - 330, h - 8), FONT_CV, 0.4, (150, 150, 150), 1)

    return canvas


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PLAYBACK LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def run_playback(model_path, sample_path, label_path, device):
    model, c2i, i2c = load_model(model_path, device)
    sos_idx = c2i["<SOS>"]
    eos_idx = c2i["<EOS>"]

    # Load and preprocess
    frames_raw = np.load(sample_path).astype(np.float32)   # (T, 75)
    print(f"[Playback] Frames: {frames_raw.shape}")

    with open(label_path, encoding="utf-8") as f:
        ground_truth = f.read().strip()
    print(f"[Playback] Label: {ground_truth}")

    frames_display = preprocess_frames(frames_raw)   # normalised for drawing
    total_frames   = len(frames_raw)
    delay_ms       = max(1, int(1000 / PLAYBACK_FPS))

    # Check Arabic rendering
    if arabic_reshaper_mod is None:
        print("\n[WARN] Arabic text will show as ???")
        print("  Fix with:  pip install arabic-reshaper python-bidi\n")
    else:
        print("[OK] Arabic rendering available\n")

    # State
    frame_idx       = 0
    buf_size        = 0
    prediction      = ""
    correct         = False
    paused          = False
    last_pred_frame = -STEP_FRAMES

    print("Controls: SPACE=pause  R=restart  S=screenshot  Q=quit\n")

    while True:
        canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)

        # Draw skeleton
        joints = frame_to_pixels(frames_display[frame_idx])
        draw_skeleton(canvas, joints)

        # Draw UI (Arabic text via PIL)
        canvas = draw_ui(canvas, frame_idx, total_frames, buf_size,
                         ground_truth, prediction, correct, paused)

        cv2.imshow("Arabic Sign Language — Playback Demo", canvas)

        key = cv2.waitKey(delay_ms) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            paused = not paused
            print("Paused." if paused else "Resumed.")
        elif key == ord("r"):
            frame_idx, buf_size = 0, 0
            prediction, correct = "", False
            last_pred_frame = -STEP_FRAMES
            print("Restarted.")
            continue
        elif key == ord("s"):
            fname = f"screenshot_{frame_idx}.jpg"
            cv2.imwrite(fname, canvas)
            print(f"Saved {fname}")

        if not paused:
            buf_size = frame_idx + 1

            # Predict
            if (buf_size >= MIN_FRAMES and
                    frame_idx - last_pred_frame >= STEP_FRAMES):
                last_pred_frame = frame_idx
                seq     = frames_raw[:buf_size]
                x       = torch.tensor(seq, dtype=torch.float32).to(device)
                indices = model.translate(x, sos_idx, eos_idx, max_len=20)
                prediction = decode_indices(indices, i2c)
                correct    = prediction.strip() == ground_truth.strip()
                if prediction:
                    tag = "✓" if correct else "✗"
                    print(f"  Frame {frame_idx:>3}/{total_frames} | {tag} pred: '{prediction}'")

            # Advance — loop at end
            frame_idx += 1
            if frame_idx >= total_frames:
                frame_idx       = 0
                buf_size        = 0
                last_pred_frame = -STEP_FRAMES
                print("--- Loop ---")

    cv2.destroyAllWindows()
    print("Done.")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model",  required=True)
    p.add_argument("--sample", required=True)
    p.add_argument("--label",  required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--fps",    type=int, default=12)
    return p.parse_args()


if __name__ == "__main__":
    args         = parse_args()
    PLAYBACK_FPS = args.fps
    device       = torch.device(args.device)
    print(f"\n[Demo] model={args.model}  sample={args.sample}  fps={PLAYBACK_FPS}\n")
    run_playback(args.model, args.sample, args.label, torch.device(args.device))
