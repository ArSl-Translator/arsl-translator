import argparse
import contextlib
import os

import mlflow
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader

from src.models.landmark_lstm import LandmarkBiLSTMClassifier
from src.train.mediapipe_dataset import KArSLMediaPipeDataset
from src.train.trainer import evaluate, train_one_epoch
from src.utils.io import ensure_dir


def parse_args():
    p = argparse.ArgumentParser(description="Train KArSL-502 from pre-extracted MediaPipe Pose CSV sequences")
    p.add_argument("--manifest_csv", default="./outputs/mediapipe/mediapipe_manifest.csv")
    p.add_argument("--num_frames", type=int, default=64)
    p.add_argument("--input_dim", type=int, default=None, help="Auto-detected from manifest if omitted")
    p.add_argument("--use_signer", default="all", help="01, 02, 03, or all")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--hidden_size", type=int, default=256)
    p.add_argument("--lstm_layers", type=int, default=2)
    p.add_argument("--dropout", type=float, default=0.3)
    p.add_argument("--val_ratio", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max_samples", type=int, default=None)
    p.add_argument("--artifact_dir", default="./artifacts/models")
    p.add_argument("--experiment", default="karsl_mediapipe")
    p.add_argument("--run_name", default="landmark_bilstm")
    p.add_argument("--resume", default=None)
    p.add_argument("--no_mlflow", action="store_true")
    return p.parse_args()


def _load_checkpoint(path: str, map_location):
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)


def _mlflow_call(fn, desc: str, args):
    if args.no_mlflow:
        return None
    try:
        return fn()
    except Exception as exc:
        print(f"Warning: MLflow {desc} skipped: {exc}")
        return None


def main():
    args = parse_args()
    torch.manual_seed(args.seed)

    df = pd.read_csv(args.manifest_csv)
    if args.use_signer != "all":
        df = df[df["signer"].astype(str).str.zfill(2) == str(args.use_signer).zfill(2)].copy()

    if args.max_samples is not None and len(df) > args.max_samples:
        df = df.sample(n=args.max_samples, random_state=args.seed).copy()

    if df.empty:
        raise RuntimeError("No samples found after filtering. Check --manifest_csv and --use_signer.")

    input_dim = args.input_dim or int(df["feature_dim"].mode().iloc[0])
    df = df[df["feature_dim"].astype(int) == input_dim].copy()

    df_train = df[df["split"] == "train"].copy()
    df_test = df[df["split"] == "test"].copy()
    if df_train.empty or df_test.empty:
        raise RuntimeError("Train or test split is empty. Check the prepared manifest.")

    y = df_train["label_id"].astype(int).values
    use_stratify = y if args.max_samples is None else None
    train_df, val_df = train_test_split(
        df_train,
        test_size=args.val_ratio,
        random_state=args.seed,
        stratify=use_stratify,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_ds = KArSLMediaPipeDataset(train_df, num_frames=args.num_frames)
    val_ds = KArSLMediaPipeDataset(val_df, num_frames=args.num_frames)
    test_ds = KArSLMediaPipeDataset(df_test, num_frames=args.num_frames)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=(device == "cuda"))
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=(device == "cuda"))
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=(device == "cuda"))

    ensure_dir(args.artifact_dir)
    best_path = os.path.join(args.artifact_dir, "karsl_mediapipe_bilstm_best.pt")
    last_path = os.path.join(args.artifact_dir, "karsl_mediapipe_bilstm_last.pt")

    model = LandmarkBiLSTMClassifier(
        input_dim=input_dim,
        num_classes=502,
        hidden_size=args.hidden_size,
        lstm_layers=args.lstm_layers,
        dropout=args.dropout,
    ).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    start_epoch = 1
    best_val_top1 = -1.0

    if args.resume:
        ckpt = _load_checkpoint(args.resume, device)
        model.load_state_dict(ckpt["model_state_dict"])
        if "optimizer_state_dict" in ckpt:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = int(ckpt["epoch"]) + 1
        best_val_top1 = float(ckpt.get("best_val_top1", -1.0))
        print(f"Resuming from {args.resume} at epoch {start_epoch}")

    if not args.no_mlflow:
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        _mlflow_call(lambda: mlflow.set_tracking_uri(tracking_uri), "set_tracking_uri", args)
        _mlflow_call(lambda: mlflow.set_experiment(args.experiment), "set_experiment", args)

    run_cm = contextlib.nullcontext()
    if not args.no_mlflow:
        try:
            run_cm = mlflow.start_run(run_name=args.run_name)
        except Exception as exc:
            print(f"Warning: MLflow start_run failed ({exc}); continuing without MLflow.")

    with run_cm:
        params = vars(args).copy()
        params.update(
            {
                "device": device,
                "input_dim": input_dim,
                "train_samples": len(train_df),
                "val_samples": len(val_df),
                "test_samples": len(df_test),
            }
        )
        if not args.no_mlflow:
            _mlflow_call(lambda: mlflow.log_params(params), "log_params", args)

        for epoch in range(start_epoch, args.epochs + 1):
            tr = train_one_epoch(model, train_loader, optimizer, criterion, device)
            va = evaluate(model, val_loader, criterion, device, desc="val")

            print(
                f"Epoch {epoch:02d} | "
                f"train top1={tr['top1']:.4f} top5={tr['top5']:.4f} loss={tr['loss']:.4f} | "
                f"val top1={va['top1']:.4f} top5={va['top5']:.4f} loss={va['loss']:.4f}"
            )

            if not args.no_mlflow:
                _mlflow_call(
                    lambda: mlflow.log_metrics(
                        {
                            "train_loss": tr["loss"],
                            "train_top1": tr["top1"],
                            "train_top5": tr["top5"],
                            "val_loss": va["loss"],
                            "val_top1": va["top1"],
                            "val_top5": va["top5"],
                        },
                        step=epoch,
                    ),
                    "log_metrics",
                    args,
                )

            if va["top1"] > best_val_top1:
                best_val_top1 = va["top1"]
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "epoch": epoch,
                        "val_top1": best_val_top1,
                        "input_dim": input_dim,
                        "model_type": "karsl_mediapipe_bilstm",
                        "args": vars(args),
                    },
                    best_path,
                )

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "epoch": epoch,
                    "best_val_top1": best_val_top1,
                    "input_dim": input_dim,
                    "model_type": "karsl_mediapipe_bilstm",
                    "args": vars(args),
                },
                last_path,
            )

        ckpt = _load_checkpoint(best_path, device)
        model.load_state_dict(ckpt["model_state_dict"])
        te = evaluate(model, test_loader, criterion, device, desc="test")
        print("\nBest model saved:", best_path)
        print("Last training state:", last_path)
        print(f"Test results: top1={te['top1']:.4f}, top5={te['top5']:.4f}, loss={te['loss']:.4f}")


if __name__ == "__main__":
    main()
