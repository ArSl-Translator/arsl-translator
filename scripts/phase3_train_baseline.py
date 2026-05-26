import os
import argparse
import contextlib
import pandas as pd

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from sklearn.model_selection import train_test_split

import mlflow

from src.models.baseline_resnet_lstm import ResNetLSTMClassifier
from src.train.dataset import KArSLFramesDataset
from src.train.trainer import train_one_epoch, evaluate
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
    p.add_argument(
        "--resume",
        default=None,
        help="Path to a training checkpoint (.pt) from a previous run to continue. "
        "Saves each epoch to baseline_resnet18_bilstm_last.pt — use that file after an interrupt.",
    )
    p.add_argument(
        "--no_mlflow",
        action="store_true",
        help="Disable MLflow (offline / no tracking server). Training and checkpoints still run.",
    )

    return p.parse_args()


def _mlflow_call(fn, desc: str, args_ns):
    if args_ns.no_mlflow:
        return None
    try:
        return fn()
    except Exception as e:
        print(f"Warning: MLflow {desc} skipped: {e}")
        return None


def _load_checkpoint(path: str, map_location):
    """Load full training checkpoint (model + optimizer); PyTorch 2.6+ needs weights_only=False."""
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)


def main():
    args = parse_args()
    torch.manual_seed(args.seed)

    if not args.no_mlflow:
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        _mlflow_call(lambda: mlflow.set_tracking_uri(tracking_uri), "set_tracking_uri", args)
        _mlflow_call(lambda: mlflow.set_experiment(args.experiment), "set_experiment", args)

    df = pd.read_csv(args.index_csv)

    # Optional: filter by signer
    if args.use_signer != "all":
        signer_int = int(args.use_signer)
        df = df[pd.to_numeric(df["signer"], errors="coerce") == signer_int].copy()

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

    ensure_dir(args.artifact_dir)
    best_path = os.path.join(args.artifact_dir, "baseline_resnet18_bilstm_best.pt")
    last_path = os.path.join(args.artifact_dir, "baseline_resnet18_bilstm_last.pt")

    resume_from = args.resume
    if resume_from and not os.path.isfile(resume_from):
        raise FileNotFoundError(f"Resume checkpoint not found: {resume_from}")

    if resume_from:
        print(f"Resuming from checkpoint: {resume_from}")
        model = ResNetLSTMClassifier(num_classes=502, backbone="resnet18", pretrained=False).to(device)
        ckpt = _load_checkpoint(resume_from, device)
        model.load_state_dict(ckpt["model_state_dict"])
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        if "optimizer_state_dict" in ckpt:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = int(ckpt["epoch"]) + 1
        best_val_top1 = float(ckpt.get("best_val_top1", -1.0))
        if start_epoch > args.epochs:
            print(f"Checkpoint already completed epoch {ckpt['epoch']}; nothing to do (requested --epochs {args.epochs}).")
            return
        print(f"Continuing from epoch {start_epoch} (best val top1 so far: {best_val_top1:.4f})")
    else:
        model = ResNetLSTMClassifier(num_classes=502, backbone="resnet18", pretrained=True).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        start_epoch = 1
        best_val_top1 = -1.0

    run_cm = contextlib.nullcontext()
    if not args.no_mlflow:
        try:
            run_cm = mlflow.start_run(run_name=args.run_name)
        except Exception as e:
            print(f"Warning: MLflow start_run failed ({e}); continuing without MLflow.")

    with run_cm:
        # Log params
        params = {
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
            "resume": resume_from or "",
            "start_epoch": start_epoch,
        }
        if not args.no_mlflow:
            _mlflow_call(lambda: mlflow.log_params(params), "log_params", args)

        for epoch in range(start_epoch, args.epochs + 1):
            tr = train_one_epoch(model, train_loader, optimizer, criterion, device)
            va = evaluate(model, val_loader, criterion, device, desc="val")

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

            # Full training state every epoch (resume / crash recovery)
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "best_val_top1": best_val_top1,
                "args": vars(args),
            }, last_path)

        # Final test evaluation using best checkpoint
        if not os.path.isfile(best_path):
            raise RuntimeError(
                "No best checkpoint was written (empty training?). "
                f"Expected at: {best_path}"
            )
        ckpt = _load_checkpoint(best_path, device)
        model.load_state_dict(ckpt["model_state_dict"])

        te = evaluate(model, test_loader, criterion, device, desc="test")
        if not args.no_mlflow:
            _mlflow_call(
                lambda: mlflow.log_metrics(
                    {
                        "test_loss": te["loss"],
                        "test_top1": te["top1"],
                        "test_top5": te["top5"],
                    }
                ),
                "log_metrics test",
                args,
            )
            _mlflow_call(lambda: mlflow.log_artifact(best_path, artifact_path="models"), "log_artifact", args)
            _mlflow_call(
                lambda: mlflow.pytorch.log_model(
                    pytorch_model=model,
                    artifact_path="pytorch_model",
                    registered_model_name="karsl_baseline_resnet18_bilstm",
                ),
                "log_model",
                args,
            )

        print("\n✅ Best model saved:", best_path)
        print(f"✅ Last training state (resume): {last_path}")
        if not args.no_mlflow:
            print("✅ Model registered in MLflow Model Registry as 'karsl_baseline_resnet18_bilstm' (if server allowed)")
        print(f"✅ Test results: top1={te['top1']:.4f}, top5={te['top5']:.4f}, loss={te['loss']:.4f}")
        if not args.no_mlflow:
            print(f"✅ MLflow: {os.environ.get('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")

if __name__ == "__main__":
    main()
