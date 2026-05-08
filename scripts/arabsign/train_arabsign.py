"""
train_arabsign.py
=================
Complete ArabSign Skeleton → Arabic text training pipeline.
Architecture: Bidirectional GRU Encoder + Bahdanau Attention + GRU Decoder.

MAT file format (confirmed):
    body: (1, T) structured array
      └─ Position: (3, 25) float64  — no object wrapping, direct array

Folder structure (confirmed):
    Skeleton/01/train/0001/*.mat   (NO inner duplicate folder)
    Skeleton/01/test/0001/*.mat

Feature extraction:
    Position (3, 25) → transpose → (25, 3) → flatten → 75 features/frame
    Result per sample: (T, 75)

Run on Colab:
    !python train_arabsign.py \\
        --skeleton_root /content/Skeleton \\
        --ground_truth  /content/Skeleton/groundTruth.xlsx \\
        --exp_name      run_01
"""

from __future__ import annotations

import argparse
import codecs
import math
import os
import random
import glob

import nltk
import numpy as np
import pandas as pd
import scipy.io as sio
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset
from torch.utils.tensorboard import SummaryWriter
from torchmetrics import WordErrorRate as WER
from tqdm import tqdm

nltk.download("punkt", quiet=True)

# ─── Constants ─────────────────────────────────────────────────────────────────
FEATURE_DIM = 75          # 25 Kinect joints × 3 (X, Y, Z)
PAD, SOS, EOS = "<PAD>", "<SOS>", "<EOS>"
SPECIAL = {PAD, SOS, EOS}

# ─── Defaults ──────────────────────────────────────────────────────────────────
DEFAULTS = dict(
    skeleton_root = ".",
    ground_truth  = "groundTruth.xlsx",
    exp_name      = "arabsign_run1",
    results_dir   = "results",
    num_epochs    = 150,
    batch_size    = 16,
    learning_rate = 1e-3,
    teacher_force = 0.5,
    val_split     = 0.2,
    max_seq_len   = 300,
    hidden_size   = 512,
    num_layers    = 3,
    enc_dropout   = 0.4,
    dec_dropout   = 0.4,
    decoder_embed = 300,
    seed          = 42,
    num_workers   = 2,
    save_best     = True,
    device        = "cuda" if torch.cuda.is_available() else "cpu",
)


# ═══════════════════════════════════════════════════════════════════════════════
# MAT LOADING  (fixed)
# ═══════════════════════════════════════════════════════════════════════════════

def load_mat_skeleton(mat_path: str) -> np.ndarray | None:
    """
    Load one ArabSign .mat file → float32 (T, 75).

    body is a (1, T) structured array.
    body[i]["Position"] is already (3, 25) float64 — no object unwrapping needed.
    Transpose to (25, 3) then flatten to 75 features.
    """
    try:
        mat = sio.loadmat(mat_path)
    except Exception as e:
        print(f"[WARN] Cannot load {mat_path}: {e}")
        return None

    body = mat.get("body")
    if body is None:
        return None

    try:
        body_flat = body.flatten()          # (T,)
        T = len(body_flat)
        frames = np.empty((T, FEATURE_DIM), dtype=np.float32)

        for i in range(T):
            pos = body_flat[i]["Position"]  # already (3, 25) float64
            # transpose → (25, 3) → flatten → (75,)
            frames[i] = np.array(pos, dtype=np.float32).T.flatten()

        return frames   # (T, 75)

    except Exception as e:
        print(f"[WARN] Extraction failed for {mat_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VOCABULARY
# ═══════════════════════════════════════════════════════════════════════════════

def build_vocab(sentences: list[str]):
    tokenized = [[SOS] + s.strip().split() + [EOS] for s in sentences]
    max_len   = max(len(t) for t in tokenized)
    padded    = [t + [PAD] * (max_len - len(t)) for t in tokenized]

    c2i = {PAD: 0, SOS: 1, EOS: 2}
    idx = 3
    for caption in padded:
        for tok in caption:
            if tok not in c2i:
                c2i[tok] = idx
                idx += 1

    i2c = {v: k for k, v in c2i.items()}
    print(f"[Vocab] {len(c2i)} tokens  ({len(c2i)-3} Arabic words)  max_len={max_len}")
    return c2i, i2c, padded, max_len


# ═══════════════════════════════════════════════════════════════════════════════
# DATASET  (fixed path — no inner duplicate folder)
# ═══════════════════════════════════════════════════════════════════════════════

def discover_samples(skeleton_root: str, split: str) -> list[dict]:
    """
    Walk Skeleton/XX/{train,test}/SSSS/*.mat
    Structure: Skeleton/01/train/0001/*.mat  (single signer folder level)
    """
    samples = []
    for signer_dir in sorted(glob.glob(os.path.join(skeleton_root, "*"))):
        if not os.path.isdir(signer_dir):
            continue
        signer_name = os.path.basename(signer_dir)
        split_dir   = os.path.join(signer_dir, split)
        if not os.path.isdir(split_dir):
            continue
        for sent_dir in sorted(glob.glob(os.path.join(split_dir, "*"))):
            sid = os.path.basename(sent_dir).zfill(4)
            for mp in sorted(glob.glob(os.path.join(sent_dir, "*.mat"))):
                samples.append({
                    "mat_path":    mp,
                    "signer":      signer_name,
                    "sentence_id": sid,
                })
    return samples


class ArabSignDataset(Dataset):
    def __init__(self, skeleton_root, id2sentence, c2i, padded_captions,
                 sentence_ids, split, max_seq_len=None, signers=None):
        self.id2sentence     = id2sentence
        self.c2i             = c2i
        self.padded_captions = padded_captions
        self.sentence_ids    = sentence_ids
        self.max_seq_len     = max_seq_len

        all_s = discover_samples(skeleton_root, split)
        if signers:
            all_s = [s for s in all_s if s["signer"] in signers]
        self.samples = [s for s in all_s if s["sentence_id"] in id2sentence]
        print(f"[Dataset] split={split:5s}  samples={len(self.samples):,}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s   = self.samples[idx]
        arr = load_mat_skeleton(s["mat_path"])
        if arr is None or arr.shape[0] == 0:
            arr = np.zeros((1, FEATURE_DIM), dtype=np.float32)
        if self.max_seq_len and arr.shape[0] > self.max_seq_len:
            arr = arr[:self.max_seq_len]
        x = torch.tensor(arr, dtype=torch.float32)

        sent_idx = self.sentence_ids.index(s["sentence_id"])
        tokens   = self.padded_captions[sent_idx]
        y = torch.tensor([self.c2i[t] for t in tokens], dtype=torch.long)
        return x, y


def collate_fn(batch, pad_idx):
    xs, ys = zip(*batch)
    xs_pad = pad_sequence(xs, batch_first=True, padding_value=0.0)
    ys_pad = pad_sequence(ys, batch_first=True, padding_value=pad_idx)
    x_lens = torch.tensor([x.shape[0] for x in xs], dtype=torch.long)
    return xs_pad, ys_pad, x_lens


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
        emb     = self.dropout(self.embedding(token)).unsqueeze(0)  # (1, B, E)
        attn    = self.attention(hidden[-1], enc_out)               # (B, 1, T)
        context = attn.bmm(enc_out).permute(1, 0, 2)               # (1, B, H)
        out, hidden = self.gru(torch.cat([emb, context], dim=2), hidden)
        pred    = self.out(torch.cat([out.squeeze(0), context.squeeze(0)], dim=1))
        return F.log_softmax(pred, dim=1), hidden, attn


class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder, vocab_size):
        super().__init__()
        self.encoder    = encoder
        self.decoder    = decoder
        self.vocab_size = vocab_size

    def forward(self, src, tgt, teacher_force_ratio=0.5):
        B, L    = tgt.shape
        device  = src.device
        outputs = torch.zeros(L, B, self.vocab_size, device=device)
        guesses = torch.zeros(L, B, dtype=torch.long, device=device)

        enc_out, hidden = self.encoder(src)
        x = tgt[:, 0]

        for t in range(1, L):
            out, hidden, _ = self.decoder(x, enc_out, hidden)
            outputs[t]     = out
            best           = out.argmax(1)
            guesses[t]     = best
            x = tgt[:, t] if random.random() < teacher_force_ratio else best

        return outputs, guesses


# ═══════════════════════════════════════════════════════════════════════════════
# INFERENCE & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@torch.no_grad()
def greedy_decode(model, src, tgt):
    B, L    = tgt.shape
    device  = src.device
    outputs = torch.zeros(L, B, model.vocab_size, device=device)
    guesses = torch.zeros(L, B, dtype=torch.long, device=device)

    enc_out, hidden = model.encoder(src)
    x = tgt[:, 0]
    for t in range(1, L):
        out, hidden, _ = model.decoder(x, enc_out, hidden)
        outputs[t]     = out
        x = guesses[t] = out.argmax(1)
    return outputs, guesses


def decode_sentence(indices, i2c):
    words = []
    for i in indices:
        i   = int(i.item()) if isinstance(i, torch.Tensor) else int(i)
        tok = i2c.get(i, "")
        if tok and tok not in SPECIAL:
            words.append(tok)
    return " ".join(words)


def compute_bleu(cands, refs):
    scores, n = [0.0] * 4, max(len(cands), 1)
    weights   = [(1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)]
    for c, r in zip(cands, refs):
        c, r = c.split(), r.split()
        for i, w in enumerate(weights):
            scores[i] += nltk.translate.bleu_score.sentence_bleu([r], c, weights=w)
    return [s / n for s in scores]


def evaluate(model, loader, criterion, i2c, device, pad_idx):
    wer_fn     = WER()
    model.eval()
    total_loss = 0.0
    all_true, all_pred = [], []

    with torch.no_grad():
        for xs, ys, _ in loader:
            xs, ys = xs.to(device), ys.to(device)
            outputs, preds = greedy_decode(model, xs, ys)
            loss = criterion(
                outputs[1:].reshape(-1, outputs.shape[2]),
                ys.permute(1, 0)[1:].reshape(-1)
            )
            total_loss += loss.item()
            for cap, pred in zip(ys[:, 1:], preds.permute(1, 0)[:, 1:]):
                all_true.append(decode_sentence(cap.cpu().numpy(), i2c))
                all_pred.append(decode_sentence(pred.cpu().numpy(), i2c))

    return total_loss / len(loader), wer_fn(all_pred, all_true).item(), all_true, all_pred


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════════════════════

def train(cfg):
    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])

    device  = torch.device(cfg["device"])
    exp_dir = os.path.join(cfg["results_dir"], cfg["exp_name"])
    os.makedirs(exp_dir, exist_ok=True)

    print(f"\n[Config] device={device}  epochs={cfg['num_epochs']}  "
          f"batch={cfg['batch_size']}  hidden={cfg['hidden_size']}\n")

    # ── Vocabulary ────────────────────────────────────────────────────────
    gt = pd.read_excel(cfg["ground_truth"], dtype=str)
    gt["SentenceID"] = gt["SentenceID"].str.zfill(4)
    sent_ids    = gt["SentenceID"].tolist()
    sentences   = gt["Sentence"].tolist()
    id2sentence = dict(zip(sent_ids, sentences))

    c2i, i2c, padded_captions, max_label_len = build_vocab(sentences)
    vocab_size = len(c2i)
    pad_idx    = c2i[PAD]

    # ── Datasets ──────────────────────────────────────────────────────────
    ds_kw = dict(
        skeleton_root   = cfg["skeleton_root"],
        id2sentence     = id2sentence,
        c2i             = c2i,
        padded_captions = padded_captions,
        sentence_ids    = sent_ids,
        max_seq_len     = cfg["max_seq_len"],
    )
    train_ds = ArabSignDataset(split="train", **ds_kw)
    test_ds  = ArabSignDataset(split="test",  **ds_kw)

    n_val = int(len(train_ds) * cfg["val_split"])
    train_ds, val_ds = torch.utils.data.random_split(
        train_ds, [len(train_ds) - n_val, n_val],
        generator=torch.Generator().manual_seed(cfg["seed"])
    )
    print(f"\n[Split] train={len(train_ds)}  val={len(val_ds)}  test={len(test_ds)}\n")

    _col = lambda b: collate_fn(b, pad_idx)
    lkw  = dict(batch_size=cfg["batch_size"], num_workers=cfg["num_workers"],
                collate_fn=_col, pin_memory=device.type == "cuda")
    train_loader = DataLoader(train_ds, shuffle=True,  **lkw)
    val_loader   = DataLoader(val_ds,   shuffle=False, **lkw)
    test_loader  = DataLoader(test_ds,  shuffle=False, **lkw)

    # ── Model ─────────────────────────────────────────────────────────────
    encoder = Encoder(FEATURE_DIM, cfg["hidden_size"],
                      cfg["num_layers"], cfg["enc_dropout"]).to(device)
    decoder = Decoder(vocab_size, cfg["decoder_embed"], cfg["hidden_size"],
                      cfg["num_layers"], cfg["dec_dropout"]).to(device)
    model     = Seq2Seq(encoder, decoder, vocab_size).to(device)
    optimizer = optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    criterion = nn.CrossEntropyLoss(ignore_index=pad_idx)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Model] feature_dim={FEATURE_DIM}  vocab_size={vocab_size}  "
          f"params={n_params:,}\n")

    writer        = SummaryWriter(os.path.join(exp_dir, "tensorboard"))
    best_val_loss = float("inf")
    history, step = [], 0

    # ── Training loop ─────────────────────────────────────────────────────
    for epoch in range(1, cfg["num_epochs"] + 1):
        model.train()
        running_loss = 0.0
        prog = tqdm(train_loader, desc=f"Epoch {epoch:>3}/{cfg['num_epochs']}", leave=True)

        for xs, ys, _ in prog:
            xs, ys = xs.to(device), ys.to(device)
            outputs, _ = model(xs, ys, cfg["teacher_force"])
            out_flat   = outputs[1:].reshape(-1, vocab_size)
            tgt_flat   = ys.permute(1, 0)[1:].reshape(-1)

            optimizer.zero_grad()
            loss = criterion(out_flat, tgt_flat)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            running_loss += loss.item()
            writer.add_scalar("Loss/train_step", loss.item(), step)
            step += 1
            prog.set_postfix(loss=f"{loss.item():.4f}")

        train_loss = running_loss / len(train_loader)
        val_loss, val_wer, _, _ = evaluate(
            model, val_loader, criterion, i2c, device, pad_idx
        )

        print(f"  Epoch {epoch:>3} | train={train_loss:.4f} | "
              f"val={val_loss:.4f} | WER={val_wer:.3f}")
        writer.add_scalar("Loss/train", train_loss, epoch)
        writer.add_scalar("Loss/val",   val_loss,   epoch)
        writer.add_scalar("WER/val",    val_wer,    epoch)

        history.append({"epoch": epoch, "train_loss": train_loss,
                        "val_loss": val_loss, "val_wer": val_wer})

        if cfg["save_best"] and val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "epoch":           epoch,
                "model_state":     model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "val_loss":        val_loss,
                "val_wer":         val_wer,
                "cfg":             cfg,
                "c2i":             c2i,
                "i2c":             i2c,
                "vocab_size":      vocab_size,
            }, os.path.join(exp_dir, "best_model.pt"))
            print(f"  ✓ Saved best (val_loss={val_loss:.4f})")

    # ── Test ──────────────────────────────────────────────────────────────
    print("\n[Test] Loading best model...")
    ckpt = torch.load(os.path.join(exp_dir, "best_model.pt"), map_location=device)
    model.load_state_dict(ckpt["model_state"])

    test_loss, test_wer, all_true, all_pred = evaluate(
        model, test_loader, criterion, i2c, device, pad_idx
    )
    b1, b2, b3, b4 = compute_bleu(all_pred, all_true)

    print(f"\n{'='*50}")
    print(f"  Test Loss        : {test_loss:.4f}")
    print(f"  Test WER         : {test_wer:.4f}  ({test_wer*100:.1f}%)")
    print(f"  BLEU-1/2/3/4     : {b1:.3f} / {b2:.3f} / {b3:.3f} / {b4:.3f}")
    print(f"{'='*50}\n")

    with codecs.open(os.path.join(exp_dir, "predictions.txt"), "w", "utf-8") as f:
        for t, p in zip(all_true, all_pred):
            f.write(f"{t}\t{p}\n")
    pd.DataFrame(history).to_csv(os.path.join(exp_dir, "history.csv"), index=False)
    with open(os.path.join(exp_dir, "test_metrics.txt"), "w", "utf-8") as f:
        f.write(f"test_loss\t{test_loss:.4f}\ntest_wer\t{test_wer:.4f}\n"
                f"bleu_1\t{b1:.4f}\nbleu_2\t{b2:.4f}\n"
                f"bleu_3\t{b3:.4f}\nbleu_4\t{b4:.4f}\n")
    writer.close()
    print(f"[Done] Results → {exp_dir}/")

    print("\n[Sample Predictions]")
    for i in range(min(8, len(all_true))):
        print(f"  TRUE: {all_true[i]}\n  PRED: {all_pred[i]}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        if isinstance(v, bool):
            p.add_argument(f"--{k}", default=v, action="store_true")
        else:
            p.add_argument(f"--{k}", default=v,
                           type=type(v) if v is not None else str)
    return vars(p.parse_args())


if __name__ == "__main__":
    cfg = parse_args()
    print("\n[Config]")
    for k, v in cfg.items():
        print(f"  {k:<20} = {v}")
    train(cfg)
