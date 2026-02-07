import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

LABEL_RE = re.compile(r"_(\d{4})_")  # finds _0001_ in folder name like 01_01_0001_(...)

def is_image_file(name: str) -> bool:
    n = name.lower()
    return n.endswith(".jpg") or n.endswith(".jpeg") or n.endswith(".png")

@dataclass
class IndexConfig:
    dataset_root: str                 # path to folder containing 01,02,03
    output_csv: str                   # where to save data_index.csv
    signers: Tuple[str, ...] = ("01", "02", "03")
    splits: Tuple[str, ...] = ("train", "test")

def extract_label_id_from_folder(folder_name: str) -> Optional[Tuple[int, str]]:
    """
    Returns (label_id_int, label_id_str) e.g. (65, "0065")
    """
    m = LABEL_RE.search(folder_name)
    if not m:
        return None
    label_str = m.group(1)
    return int(label_str), label_str

def build_data_index(cfg: IndexConfig) -> pd.DataFrame:
    rows: List[Dict] = []
    sample_id = 0

    for signer in cfg.signers:
        for split in cfg.splits:
            split_root = os.path.join(cfg.dataset_root, signer, split)
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

    # Expected total if dataset is complete:
    expected_total = 502 * 3 * 50  # 75,300
    if len(df) != expected_total:
        print(f"\n[WARN] Total samples != expected ({expected_total}).")
        print("Possible causes: incomplete extraction, missing folders, or naming mismatch.")
    else:
        print("\n[OK] Total samples match expected 75,300.")

    # Label range check
    bad = df[(df["label_id"] < 1) | (df["label_id"] > 502)]
    if len(bad) > 0:
        print(f"\n[WARN] Found {len(bad)} samples with label outside 1..502. Example:")
        print(bad.head(5))
    else:
        print("\n[OK] All labels within 1..502.")


