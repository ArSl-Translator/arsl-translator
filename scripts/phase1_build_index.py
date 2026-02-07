import os
from src.data_prep.build_index import IndexConfig, build_data_index, summarize_and_validate
from src.utils.io import ensure_dir, read_env_default

def main():
    dataset_root = read_env_default("DATASET_ROOT", "./data/raw/KArSL")
    output_dir = read_env_default("OUTPUT_DIR", "./outputs/index")
    ensure_dir(output_dir)

    output_csv = os.path.join(output_dir, "data_index.csv")

    cfg = IndexConfig(
        dataset_root=dataset_root,
        output_csv=output_csv,
    )

    df = build_data_index(cfg)
    df.to_csv(output_csv, index=False)

    print("Saved:", os.path.abspath(output_csv))
    summarize_and_validate(df)


if __name__ == "__main__":
    main()
