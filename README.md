# ArSL Translator (Word-Level)

This project builds a word-level Arabic Sign Language recognition system using the KArSL dataset (502 words, 3 professional signers).

## Repo layout
- `data/raw/`  -> raw dataset + labels (not committed)
- `outputs/index/` -> generated index + label maps (not committed)
- `src/data_prep/` -> dataset preparation (Phase 1 + 2)
- `scripts/` -> runnable scripts

## Phase 1 + 2 (Data preparation)
### 1) Build dataset index
Creates `outputs/index/data_index.csv` where each row = one sample (one sign repetition folder).
### 2) Build label maps
Creates `outputs/index/label2text.json` and `outputs/index/text2label.json`.

## Run
python -m venv .venv
# Windows:
#   .\.venv\Scripts\activate
pip install -r requirements.txt

# Ensure you placed:
# - dataset at: data/raw/KArSL/01 ... data/raw/KArSL/03
# - excel at:   data/raw/labels/KARSL-502_Labels.xlsx

python scripts/phase1_build_index.py
python scripts/phase2_build_labels.py

