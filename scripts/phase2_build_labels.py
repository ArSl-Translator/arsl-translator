import os
from src.data_prep.build_labels import LabelsConfig, build_label_maps, save_label_maps
from src.utils.io import read_env_default

def main():
    labels_xlsx = read_env_default("LABELS_XLSX", "./data/raw/labels/KARSL-502_Labels.xlsx")
    output_dir = read_env_default("OUTPUT_DIR", "./outputs/index")

    cfg = LabelsConfig(labels_xlsx=labels_xlsx, output_dir=output_dir)
    label2text, text2label = build_label_maps(cfg)

    save_label_maps(output_dir, label2text, text2label)

    print("Saved:")
    print(" -", os.path.abspath(os.path.join(output_dir, "label2text.json")))
    print(" -", os.path.abspath(os.path.join(output_dir, "text2label.json")))
    print("Labels found:", len(label2text))

    missing = [str(i) for i in range(1, 503) if str(i) not in label2text]
    if missing:
        print("[WARN] Missing label ids (example):", missing[:10])
    else:
        print("[OK] Found all labels 1..502")


if __name__ == "__main__":
    main()
