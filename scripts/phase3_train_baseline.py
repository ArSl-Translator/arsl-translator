import os
import argparse
import json
import pandas as pd

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from sklearn.model_selection import train_test_split

import mlflow

from src.models.baseline_resnet_lstm import ResNetLSTMClassifier
from src.train.dataset import KArSLFramesDataset
from src.train.trainer import TrainConfig, train_one_epoch, evaluate
from src.utils.io import ensure_dir


def parse_args():
    p = argparse.ArgumentParser(description="Phase 3: Baseline training (ResNet18 + BiLSTM)")
    p.add_argument("--index_csv", default="./outputs/index/data_index.csv")
    p.add_argument("--num_frames", type=int, default=32)
    p.add_argument("--img_size", type=int, default=224)

    p.add_argument("--use_signer", default="all", help="01 or 02 or 03 or all")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)

    p.add_argument("--val_ratio", type=float, default=0.1, help="validation split from TRAIN only")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max_samples", type=int, default=None, help="Limit training samples for quick testing")

    p.add_argument("--artifact_dir", default="./artifacts/models")
    p.add_argument("--experiment", default="karsl_baseline")
    p.add_argument("--run_name", default="resnet18_bilstm")

    return p.parse_args()


def main():
    args = parse_args()
    torch.manual_seed(args.seed)

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(args.experiment)

    df = pd.read_csv(args.index_csv)

    # Optional: filter by signer
    if args.use_signer != "all":
        # Convert signer to int for comparison (handles both "01" and "1" inputs)
        signer_int = int(args.use_signer)
        df = df[df["signer"] == signer_int].copy()

    # Keep train/test as provided by dataset
    df_train = df[df["split"] == "train"].copy()
    df_test = df[df["split"] == "test"].copy()

    # Optional: limit samples for quick testing
    if args.max_samples is not None:
        if len(df_train) > args.max_samples:
            df_train = df_train.sample(n=args.max_samples, random_state=args.seed).copy()
        if len(df_test) > args.max_samples // 5:  # Keep test set smaller
            df_test = df_test.sample(n=args.max_samples // 5, random_state=args.seed).copy()

    if len(df_train) == 0 or len(df_test) == 0:
        raise RuntimeError("Train or test split is empty. Check your data_index.csv and dataset paths.")

    # Create train/val split from TRAIN only (stratified by label if possible)
    y = df_train["label_id"].astype(int).values
    # Disable stratification for small sample sizes to avoid stratification errors
    use_stratify = y if args.max_samples is None else None
    train_df, val_df = train_test_split(
        df_train,
        test_size=args.val_ratio,
        random_state=args.seed,
        stratify=use_stratify,
    )

    train_ds = KArSLFramesDataset(train_df, num_frames=args.num_frames, img_size=args.img_size)
    val_ds   = KArSLFramesDataset(val_df,   num_frames=args.num_frames, img_size=args.img_size)
    test_ds  = KArSLFramesDataset(df_test,  num_frames=args.num_frames, img_size=args.img_size)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=2, pin_memory=(device=="cuda"))
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=(device=="cuda"))
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=(device=="cuda"))

    model = ResNetLSTMClassifier(num_classes=502, backbone="resnet18", pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    ensure_dir(args.artifact_dir)
    best_path = os.path.join(args.artifact_dir, "baseline_resnet18_bilstm_best.pt")

    with mlflow.start_run(run_name=args.run_name):
        # Log params
        mlflow.log_params({
            "num_frames": args.num_frames,
            "img_size": args.img_size,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "weight_decay": args.weight_decay,
            "val_ratio": args.val_ratio,
            "use_signer": args.use_signer,
            "max_samples": args.max_samples,
            "device": device,
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(df_test),
        })

        best_val_top1 = -1.0

        for epoch in range(1, args.epochs + 1):
            tr = train_one_epoch(model, train_loader, optimizer, criterion, device)
            va = evaluate(model, val_loader, criterion, device, desc="val")

            mlflow.log_metrics({
                "train_loss": tr["loss"],
                "train_top1": tr["top1"],
                "train_top5": tr["top5"],
                "val_loss": va["loss"],
                "val_top1": va["top1"],
                "val_top5": va["top5"],
            }, step=epoch)

            print(f"Epoch {epoch:02d} | "
                  f"train top1={tr['top1']:.4f} top5={tr['top5']:.4f} loss={tr['loss']:.4f} | "
                  f"val top1={va['top1']:.4f} top5={va['top5']:.4f} loss={va['loss']:.4f}")

            if va["top1"] > best_val_top1:
                best_val_top1 = va["top1"]
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_top1": best_val_top1,
                    "args": vars(args),
                }, best_path)

        # Final test evaluation using best checkpoint
        ckpt = torch.load(best_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])

        te = evaluate(model, test_loader, criterion, device, desc="test")
        mlflow.log_metrics({
            "test_loss": te["loss"],
            "test_top1": te["top1"],
            "test_top5": te["top5"],
        })

        # Log checkpoint file as artifact
        mlflow.log_artifact(best_path, artifact_path="models")

        # Log model to MLflow in pytorch format
        mlflow.pytorch.log_model(
            pytorch_model=model,
            artifact_path="pytorch_model",
            registered_model_name="karsl_baseline_resnet18_bilstm"
        )

        print("\n✅ Best model saved:", best_path)
        print(f"✅ Model registered in MLflow Model Registry as 'karsl_baseline_resnet18_bilstm'")
        print(f"✅ Test results: top1={te['top1']:.4f}, top5={te['top5']:.4f}, loss={te['loss']:.4f}")
        print(f"✅ MLflow: {os.environ.get('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")

if __name__ == "__main__":
    main()
