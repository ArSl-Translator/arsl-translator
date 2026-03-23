import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Original KArSL layout: nested folders with label embedded, e.g. ..._0001_...
LABEL_RE = re.compile(r"_(\d{4})_")
# Flat layout (e.g. Kaggle): sample folder is exactly 4 digits, e.g. 0001 / 0065 / 0502
FOLDER_LABEL_4DIGIT = re.compile(r"^(\d{4})$")

def is_image_file(name: str) -> bool:
    n = name.lower()
    return n.endswith(".jpg") or n.endswith(".jpeg") or n.endswith(".png")

@dataclass
class IndexConfig:
    dataset_root: str                 # path to folder containing signer dirs (01, 02, ...)
    output_csv: str                   # where to save data_index.csv
    signers: Optional[Tuple[str, ...]] = None  # None = auto-discover subdirs that have train/ or test/
    splits: Tuple[str, ...] = ("train", "test")


def resolve_signer_content_root(dataset_root: str, signer: str) -> Optional[str]:
    """
    Directory that contains train/ and test/ for this signer.

    Prefer DATASET_ROOT/<signer>/train|test; if missing, use DATASET_ROOT/<signer>/<signer>/train|test.
    """
    flat = os.path.join(dataset_root, signer)
    nested = os.path.join(dataset_root, signer, signer)
    flat_ok = os.path.isdir(os.path.join(flat, "train")) or os.path.isdir(os.path.join(flat, "test"))
    nested_ok = os.path.isdir(os.path.join(nested, "train")) or os.path.isdir(os.path.join(nested, "test"))
    if flat_ok:
        return flat
    if nested_ok:
        return nested
    return None


def discover_signers(dataset_root: str) -> Tuple[str, ...]:
    """
    Top-level folders under dataset_root that have train/ or test/ (flat or nested signer folder).
    Skips hidden dirs like .git or __MACOSX.
    """
    if not os.path.isdir(dataset_root):
        return ()
    found: List[str] = []
    for name in sorted(os.listdir(dataset_root)):
        path = os.path.join(dataset_root, name)
        if not os.path.isdir(path):
            continue
        if name.startswith(".") or name.startswith("__"):
            continue
        if resolve_signer_content_root(dataset_root, name) is not None:
            found.append(name)
    return tuple(found)


def extract_label_id_from_folder(folder_name: str) -> Optional[Tuple[int, str]]:
    """
    Returns (label_id_int, label_id_str) e.g. (65, "0065").

    Supports:
    - Legacy: substring like _0001_ inside folder name
    - Flat Kaggle-style: folder name is exactly four digits (0001..0502)
    """
    m = LABEL_RE.search(folder_name)
    if m:
        label_str = m.group(1)
        return int(label_str), label_str
    m2 = FOLDER_LABEL_4DIGIT.match(folder_name)
    if m2:
        label_str = m2.group(1)
        return int(label_str), label_str
    return None

def build_data_index(cfg: IndexConfig) -> pd.DataFrame:
    rows: List[Dict] = []
    sample_id = 0

    signers = cfg.signers
    if signers is None:
        signers = discover_signers(cfg.dataset_root)
        print(f"[INFO] Auto-discovered signer folders: {signers}")
    if not signers:
        print("[ERROR] No signer folders found (expected subdirs with train/ or test/).")
        return pd.DataFrame()

    for signer in signers:
        signer_root = resolve_signer_content_root(cfg.dataset_root, signer)
        if signer_root is None:
            print(
                f"[WARN] No train/ or test/ under {cfg.dataset_root}/{signer}/ "
                f"or {cfg.dataset_root}/{signer}/{signer}/ — skipping signer {signer}"
            )
            continue
        if os.path.normpath(signer_root) == os.path.normpath(os.path.join(cfg.dataset_root, signer)):
            layout = "flat"
        else:
            layout = "nested"
        print(f"[INFO] Signer {signer}: using {layout} layout → {signer_root}")

        for split in cfg.splits:
            split_root = os.path.join(signer_root, split)
            if not os.path.isdir(split_root):
                print(f"[WARN] Missing folder: {split_root}")
                continue

            # We walk through all subfolders; a "sample folder" is one that contains image frames.
            for root, _, files in os.walk(split_root):
                img_files = [f for f in files if is_image_file(f)]
                if not img_files:
                    continue

                folder_name = os.path.basename(root)
                label_info = extract_label_id_from_folder(folder_name)
                if label_info is None:
                    # If your naming differs, adjust LABEL_RE
                    print(f"[SKIP] Could not extract label from folder: {root}")
                    continue

                label_id_int, label_id_str = label_info
                n_frames = len(img_files)

                sample_id += 1
                rows.append({
                    "sample_id": sample_id,
                    "signer": signer,
                    "split": split,
                    "label_id": label_id_int,      # 1..502
                    "label_id_str": label_id_str,  # "0001".."0502"
                    "frames_dir": os.path.abspath(root),
                    "n_frames": n_frames,
                })

    df = pd.DataFrame(rows)
    return df


def summarize_and_validate(df: pd.DataFrame) -> None:
    print("\n--- Summary ---")
    print("Total samples:", len(df))
    if len(df) == 0:
        print("[ERROR] No samples found. Likely dataset path is wrong or extraction incomplete.")
        return

    print("\nBy split:")
    print(df.groupby("split").size())

    print("\nBy signer:")
    print(df.groupby("signer").size())

    # Expected total if dataset is complete (502 classes × 50 reps × N signers)
    n_signers = df["signer"].nunique()
    expected_total = 502 * n_signers * 50
    if len(df) != expected_total:
        print(f"\n[WARN] Total samples != expected ({expected_total} for {n_signers} signer(s)).")
        print("Possible causes: incomplete extraction, missing folders, or naming mismatch.")
    else:
        print(f"\n[OK] Total samples match expected {expected_total} ({n_signers} signer(s)).")

    # Label range check
    bad = df[(df["label_id"] < 1) | (df["label_id"] > 502)]
    if len(bad) > 0:
        print(f"\n[WARN] Found {len(bad)} samples with label outside 1..502. Example:")
        print(bad.head(5))
    else:
        print("\n[OK] All labels within 1..502.")


