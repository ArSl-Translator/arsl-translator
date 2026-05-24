import argparse
import hashlib
import os
from pathlib import Path
from typing import Any, Dict

import mlflow
import torch


DEFAULT_MODELS = [
    {
        "key": "karsl_mediapipe",
        "name": "KArSL MediaPipe BiLSTM",
        "path": "./models/karsl_mediapipe_bilstm_best.pt",
        "experiment": "serving_models",
    },
    {
        "key": "arabsign",
        "name": "ArabSign GRU Attention",
        "path": "./models/arabsign_best_model.pt",
        "experiment": "serving_models",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(description="Log currently served model checkpoints to MLflow.")
    parser.add_argument(
        "--tracking_uri",
        default=os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"),
        help="MLflow tracking server URI.",
    )
    parser.add_argument(
        "--artifact_path",
        default="checkpoint",
        help="Artifact folder name inside each MLflow run.",
    )
    parser.add_argument(
        "--skip_artifacts",
        action="store_true",
        help="Log metadata only. Useful when checkpoint uploads are too large.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_checkpoint_metadata(path: Path) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:
        metadata["checkpoint_read_error"] = str(exc)[:250]
        return metadata

    if isinstance(checkpoint, dict):
        for key in [
            "epoch",
            "best_val_top1",
            "val_top1",
            "input_dim",
            "model_type",
            "vocab_size",
        ]:
            if key in checkpoint:
                metadata[key] = checkpoint[key]

        args = checkpoint.get("args")
        if isinstance(args, dict):
            for key in [
                "num_frames",
                "hidden_size",
                "lstm_layers",
                "dropout",
                "batch_size",
                "lr",
                "weight_decay",
                "use_signer",
                "epochs",
            ]:
                if key in args:
                    metadata[f"arg_{key}"] = args[key]

    return metadata


def log_model_entry(entry: Dict[str, str], args) -> bool:
    model_path = Path(entry["path"])
    if not model_path.exists():
        print(f"Skipping {entry['key']}: {model_path} does not exist.")
        return False

    metadata = safe_checkpoint_metadata(model_path)
    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    file_hash = sha256_file(model_path)

    mlflow.set_experiment(entry["experiment"])
    with mlflow.start_run(run_name=f"current-{entry['key']}") as run:
        mlflow.set_tags(
            {
                "model_key": entry["key"],
                "model_name": entry["name"],
                "serving_status": "current",
                "checkpoint_path": str(model_path),
                "checkpoint_sha256": file_hash,
            }
        )
        mlflow.log_params(
            {
                "model_key": entry["key"],
                "model_name": entry["name"],
                "checkpoint_file": model_path.name,
                "checkpoint_size_mb": round(file_size_mb, 2),
                **{k: v for k, v in metadata.items() if not isinstance(v, float)},
            }
        )

        metric_values = {}
        for key in ["best_val_top1", "val_top1"]:
            value = metadata.get(key)
            if isinstance(value, (int, float)):
                metric_values[key] = float(value)
        if metric_values:
            mlflow.log_metrics(metric_values)

        if not args.skip_artifacts:
            mlflow.log_artifact(str(model_path), artifact_path=args.artifact_path)

        print(f"Logged {entry['name']} to MLflow run {run.info.run_id}.")
    return True


def main():
    args = parse_args()
    mlflow.set_tracking_uri(args.tracking_uri)
    print(f"MLflow tracking URI: {args.tracking_uri}")

    logged = 0
    for entry in DEFAULT_MODELS:
        if log_model_entry(entry, args):
            logged += 1

    print(f"Done. Logged {logged} current model run(s).")


if __name__ == "__main__":
    main()
