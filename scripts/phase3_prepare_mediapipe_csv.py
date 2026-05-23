import argparse
import os
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.utils.io import ensure_dir


LABEL_CANDIDATES = (
    "label_id",
    "label",
    "class",
    "class_id",
    "sign",
    "sign_id",
    "sentence",
    "sentence_id",
    "word_id",
)


def parse_args():
    p = argparse.ArgumentParser(
        description="Prepare KArSL MediaPipe Pose CSV files into compact per-sample .npz sequences."
    )
    p.add_argument("--csv_dir", required=True, help="Folder containing signerXX_train.csv and signerXX_test.csv")
    p.add_argument("--output_dir", default="./outputs/mediapipe")
    p.add_argument("--label_col", default=None, help="Override label column name")
    p.add_argument("--feature_dim", type=int, default=None, help="Usually 75, 99, or 132. Auto-detected if omitted.")
    p.add_argument("--chunksize", type=int, default=512)
    p.add_argument("--max_rows_per_file", type=int, default=None, help="Quick smoke-test limiter")
    p.add_argument("--dry_run", action="store_true", help="Print detected columns without writing samples")
    return p.parse_args()


def _normalize_label_id(value) -> Optional[int]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    label_id = int(match.group(1))
    if 1 <= label_id <= 502:
        return label_id
    return None


def _detect_label_col(df: pd.DataFrame, override: Optional[str]) -> str:
    if override:
        if override not in df.columns:
            raise ValueError(f"--label_col '{override}' not found. Available columns: {list(df.columns)[:30]}")
        return override

    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for candidate in LABEL_CANDIDATES:
        if candidate in lower_map:
            return lower_map[candidate]

    best_col = None
    best_score = -1
    for col in df.columns[:20]:
        normalized = [_normalize_label_id(v) for v in df[col].head(200)]
        score = sum(v is not None for v in normalized)
        if score > best_score:
            best_score = score
            best_col = col

    if best_col is None or best_score <= 0:
        raise ValueError(
            "Could not detect the label column. Re-run with --label_col after inspecting the CSV header."
        )
    return best_col


def _feature_columns(df: pd.DataFrame, label_col: str) -> list[str]:
    cols = []
    for col in df.columns:
        if col == label_col:
            continue
        numeric = pd.to_numeric(df[col].head(50), errors="coerce")
        if numeric.notna().mean() >= 0.8:
            cols.append(col)
    return cols


def _infer_feature_dim(n_features: int, requested: Optional[int]) -> int:
    if requested:
        if n_features % requested != 0:
            raise ValueError(f"{n_features} feature columns are not divisible by --feature_dim {requested}")
        return requested
    for dim in (75, 99, 132):
        if n_features % dim == 0:
            return dim
    raise ValueError(
        f"Could not infer feature_dim from {n_features} numeric feature columns. "
        "Pass --feature_dim 75, 99, or 132 after checking the CSV."
    )


def _csv_files(csv_dir: str) -> Iterable[Path]:
    return sorted(Path(csv_dir).glob("signer*_*.csv"))


def _split_and_signer(path: Path) -> tuple[str, str]:
    name = path.stem.lower()
    split = "test" if "test" in name else "train"
    signer_match = re.search(r"signer(\d+)", name)
    signer = signer_match.group(1).zfill(2) if signer_match else "unknown"
    return split, signer


def _trim_empty_tail(seq: np.ndarray) -> np.ndarray:
    non_empty = np.where(np.abs(seq).sum(axis=1) > 0)[0]
    if len(non_empty) == 0:
        return seq[:1]
    return seq[: non_empty[-1] + 1]


def prepare_file(path: Path, args, sequence_dir: str, manifest_rows: list[dict]) -> None:
    split, signer = _split_and_signer(path)
    first = pd.read_csv(path, nrows=50)
    label_col = _detect_label_col(first, args.label_col)
    feature_cols = _feature_columns(first, label_col)
    feature_dim = _infer_feature_dim(len(feature_cols), args.feature_dim)

    print(f"\n[{path.name}]")
    print(f"  split       : {split}")
    print(f"  signer      : {signer}")
    print(f"  label_col   : {label_col}")
    print(f"  feature_cols: {len(feature_cols)}")
    print(f"  feature_dim : {feature_dim}")
    print(f"  frames/row  : {len(feature_cols) // feature_dim}")

    if args.dry_run:
        return

    written = 0
    reader = pd.read_csv(path, chunksize=args.chunksize)
    with tqdm(desc=f"prepare {path.name}", unit="rows") as pbar:
        for chunk in reader:
            if args.max_rows_per_file is not None:
                remaining = args.max_rows_per_file - written
                if remaining <= 0:
                    break
                chunk = chunk.head(remaining)

            labels = chunk[label_col].map(_normalize_label_id)
            values = chunk[feature_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float32)

            for row_idx, label_id in enumerate(labels):
                if label_id is None:
                    continue
                flat = np.nan_to_num(values[row_idx], nan=0.0, posinf=0.0, neginf=0.0)
                seq = flat.reshape(-1, feature_dim)
                seq = _trim_empty_tail(seq)

                sample_id = f"{path.stem}_{written:07d}"
                rel_path = os.path.join("sequences", signer, split, f"{sample_id}.npz")
                out_path = os.path.join(args.output_dir, rel_path)
                ensure_dir(os.path.dirname(out_path))
                np.savez_compressed(out_path, features=seq)
                manifest_rows.append(
                    {
                        "npz_path": os.path.abspath(out_path),
                        "label_id": label_id,
                        "split": split,
                        "signer": signer,
                        "n_frames": int(seq.shape[0]),
                        "feature_dim": int(feature_dim),
                        "source_csv": str(path),
                    }
                )
                written += 1
            pbar.update(len(chunk))


def main():
    args = parse_args()
    ensure_dir(args.output_dir)
    sequence_dir = os.path.join(args.output_dir, "sequences")
    ensure_dir(sequence_dir)

    files = list(_csv_files(args.csv_dir))
    if not files:
        raise FileNotFoundError(f"No signer*_*.csv files found in {args.csv_dir}")

    rows: list[dict] = []
    for path in files:
        prepare_file(path, args, sequence_dir, rows)

    if args.dry_run:
        print("\nDry run complete. No files were written.")
        return

    manifest = pd.DataFrame(rows)
    manifest_path = os.path.join(args.output_dir, "mediapipe_manifest.csv")
    manifest.to_csv(manifest_path, index=False)
    print(f"\nSaved manifest: {os.path.abspath(manifest_path)}")
    print(f"Prepared samples: {len(manifest):,}")


if __name__ == "__main__":
    main()
