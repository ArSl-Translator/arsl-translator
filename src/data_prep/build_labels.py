import os
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import pandas as pd

from src.utils.io import write_json, ensure_dir

@dataclass
class LabelsConfig:
    labels_xlsx: str
    output_dir: str
    # If None, we auto-detect best columns
    id_col: Optional[str] = None
    text_col: Optional[str] = None

def _normalize_label_id(raw) -> Optional[int]:
    """
    Handles values like "0001", 1, 1.0
    """
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def _auto_pick_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Heuristic:
    - ID column: column containing mostly numeric values in 1..502
    - Text column: the most "text-like" column
    """
    cols = list(df.columns)

    # Find ID col
    best_id_col = None
    best_score = -1

    for c in cols:
        vals = df[c].head(600).tolist()
        norm = [_normalize_label_id(v) for v in vals]
        valid = [x for x in norm if x is not None and 1 <= x <= 502]
        score = len(valid)
        if score > best_score:
            best_score = score
            best_id_col = c

    if best_id_col is None:
        best_id_col = cols[0]

    # Find text col
    def textiness(c: str) -> int:
        vals = df[c].head(600).tolist()
        non_empty = [v for v in vals if not pd.isna(v) and str(v).strip() != ""]
        score = 0
        for v in non_empty:
            try:
                float(str(v).strip())
            except:
                score += 1
        return score

    best_text_col = max(cols, key=textiness)
    return best_id_col, best_text_col


def build_label_maps(cfg: LabelsConfig) -> Tuple[Dict[str, str], Dict[str, int]]:
    df = pd.read_excel(cfg.labels_xlsx)

    id_col, text_col = cfg.id_col, cfg.text_col
    if id_col is None or text_col is None:
        id_col, text_col = _auto_pick_columns(df)

    label2text: Dict[str, str] = {}
    text2label: Dict[str, int] = {}

    for _, row in df.iterrows():
        label_id = _normalize_label_id(row.get(id_col))
        if label_id is None or not (1 <= label_id <= 502):
            continue

        text = row.get(text_col)
        if pd.isna(text):
            continue
        text = str(text).strip()
        if text == "":
            continue

        label2text[str(label_id)] = text
        text2label[text] = label_id

    return label2text, text2label


def save_label_maps(output_dir: str, label2text: Dict[str, str], text2label: Dict[str, int]) -> None:
    ensure_dir(output_dir)
    write_json(os.path.join(output_dir, "label2text.json"), label2text)
    write_json(os.path.join(output_dir, "text2label.json"), text2label)
