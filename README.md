# ArSL Translator

**Arabic Sign Language Recognition System** -- an end-to-end pipeline from raw dataset to a web application where users can upload videos or use their webcam to get sign language predictions.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.2-red)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [File-by-File Breakdown](#file-by-file-breakdown)
- [Getting Started](#getting-started)
- [Data Preparation Pipeline](#data-preparation-pipeline)
- [Model Training](#model-training)
- [Web Application](#web-application)
- [API Reference](#api-reference)
- [Current Status](#current-status)
- [Next Steps & Roadmap](#next-steps--roadmap)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project implements a complete pipeline for Arabic Sign Language (ArSL) recognition using the **KArSL dataset** (502 sign classes, 3 signers, ~75,300 video samples). The system currently uses a **ResNet18 + BiLSTM** baseline model that extracts per-frame features with a CNN and models temporal relationships with a bidirectional LSTM.

### What exists today

- A 3-phase data preparation and training pipeline (index, labels, train)
- A baseline ResNet18 + BiLSTM model (only quick-tested so far, not seriously trained)
- A FastAPI backend serving predictions with JWT authentication
- A React frontend with video upload, webcam capture, prediction history, and a dashboard
- MLflow integration for experiment tracking
- Full Docker Compose deployment (Postgres, API, MLflow, Frontend)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **ML Model** | PyTorch, torchvision (ResNet18 + BiLSTM) |
| **Training** | Custom training loop, sklearn for splits, MLflow for tracking |
| **Backend** | FastAPI, SQLAlchemy, PostgreSQL, python-jose (JWT), passlib (bcrypt) |
| **Frontend** | React 18, Vite, Tailwind CSS, Axios, Recharts, Lucide icons |
| **Infrastructure** | Docker Compose, Uvicorn, Node 18 |

---

## Architecture

### System Diagram

```
┌───────────────────┐       ┌───────────────────┐       ┌────────────────────┐
│   React Frontend  │ HTTP  │   FastAPI Backend  │       │   ML Model         │
│   (Port 3000)     │──────>│   (Port 8000)      │──────>│   ResNet18 + LSTM  │
│   Vite + Tailwind │       │   Auth + Inference │       │   502 classes      │
└───────────────────┘       └────────┬──────────┘       └────────────────────┘
                                     │
                          ┌──────────┼──────────┐
                          │          │          │
                          ▼          ▼          ▼
                    ┌──────────┐ ┌────────┐ ┌────────┐
                    │ Postgres │ │ MLflow │ │ Model  │
                    │ (5432)   │ │ (5000) │ │ .pt    │
                    │ Users,   │ │ Experi-│ │ check- │
                    │ History  │ │ ments  │ │ point  │
                    └──────────┘ └────────┘ └────────┘
```

### Model Architecture

```
Input: Video/Webcam frames
    │
    ▼  Uniform sampling (T frames from the full sequence)
T frames (T × 3 × 224 × 224)
    │
    ▼  ResNet18 (pretrained on ImageNet, fc layer removed)
T feature vectors (T × 512)
    │
    ▼  Bidirectional LSTM (hidden=256, 1 layer)
Temporal encoding (T × 512)
    │
    ▼  Take last timestep → Dropout(0.2)
Context vector (512)
    │
    ▼  Fully Connected Linear layer
Logits (502) → Softmax → Top-K predictions
```

---

## Project Structure

```
arsl-translator/
│
├── src/
│   ├── data_prep/                    # Phase 1–2: data preparation modules
│   │   ├── build_index.py            #   Walks KArSL dataset, builds CSV index
│   │   └── build_labels.py           #   Reads Excel labels, creates JSON maps
│   │
│   ├── models/                       # Model architecture definitions
│   │   └── baseline_resnet_lstm.py   #   ResNet18 + BiLSTM classifier
│   │
│   ├── train/                        # Training utilities
│   │   ├── dataset.py                #   PyTorch Dataset for KArSL frames
│   │   ├── trainer.py                #   Train/evaluate loop functions
│   │   └── metrics.py                #   Top-K accuracy metric
│   │
│   ├── utils/                        # Shared utilities
│   │   └── io.py                     #   File I/O helpers (ensure_dir, write_json)
│   │
│   └── api/                          # FastAPI web application
│       ├── main.py                   #   App entry point, CORS, prediction endpoints
│       ├── inference.py              #   Model loading & preprocessing for serving
│       ├── auth/                     #   Authentication system
│       │   ├── router.py             #     Auth endpoints (register, login, change-password, profile, history)
│       │   ├── schemas.py            #     Pydantic request/response models
│       │   ├── security.py           #     JWT creation, password hashing (bcrypt)
│       │   ├── dependencies.py       #     get_current_user dependency injection
│       │   └── history_service.py    #     Saves predictions to DB for history tracking
│       ├── database/                 #   Database layer
│       │   ├── connection.py         #     SQLAlchemy engine, session factory, Base
│       │   └── init_db.py            #     create_tables() with retry logic
│       └── models/                   #   SQLAlchemy ORM models
│           ├── user.py               #     User table (email, username, password_hash)
│           └── prediction_history.py #     PredictionHistory table (type, label, confidence)
│
├── scripts/                          # Entry-point scripts for the ML pipeline
│   ├── phase1_build_index.py         #   Run phase 1: build data_index.csv
│   ├── phase2_build_labels.py        #   Run phase 2: build label JSON maps
│   └── phase3_train_baseline.py      #   Run phase 3: train ResNet18 + BiLSTM
│
├── frontend/                         # React web application
│   └── src/
│       ├── main.jsx                  #   App entry point (React StrictMode + AuthProvider)
│       ├── App.jsx                   #   Routing, layout, navigation, API status
│       ├── context/
│       │   └── AuthContext.jsx        #   Auth state management (login, register, changePassword)
│       ├── services/
│       │   └── api.js                #   Axios client with JWT interceptor
│       ├── components/
│       │   ├── VideoUpload.jsx       #   Video file upload + prediction UI
│       │   ├── WebcamCapture.jsx     #   Webcam recording + prediction UI
│       │   ├── PredictionResults.jsx #   Prediction display with confidence bars
│       │   ├── ProtectedRoute.jsx    #   Auth guard for routes
│       │   └── UserMenu.jsx          #   User dropdown (profile, sign out)
│       └── pages/
│           ├── LoginPage.jsx         #   Sign in form
│           ├── RegisterPage.jsx      #   Sign up form
│           ├── ProfilePage.jsx       #   Edit profile + change password
│           ├── HistoryPage.jsx       #   Paginated prediction history
│           └── DashboardPage.jsx     #   Usage statistics and charts
│
├── data/raw/                         # Dataset files (not committed to git)
│   ├── KArSL/                        #   KArSL dataset (01/, 02/, 03/ signer folders)
│   └── labels/                       #   KARSL-502_Labels.xlsx
│
├── outputs/index/                    # Generated by phase 1 & 2
│   ├── data_index.csv                #   Every sample: signer, split, label, frames_dir
│   ├── label2text.json               #   "1" → "Arabic text"
│   └── text2label.json               #   "Arabic text" → 1
│
├── artifacts/models/                 # Trained model checkpoints
├── mlruns/                           # MLflow experiment data
│
├── docker-compose.yml                # Defines all services (postgres, api, mlflow, frontend)
├── Dockerfile                        # Python API container image
├── requirements.base.txt             # Heavy deps (torch, opencv) — cached Docker layer
└── requirements.txt                  # Lighter deps (fastapi, auth libs)
```

---

## File-by-File Breakdown

### ML Pipeline (`src/` and `scripts/`)

#### `src/data_prep/build_index.py`

Walks the KArSL dataset directory tree (`data/raw/KArSL/{signer}/{split}/{sample_folder}/`) and builds a flat CSV index. For each sample folder that contains image frames, it extracts the label ID from the folder name using a regex (`_0001_` pattern), counts the frames, and records the absolute path. The output `data_index.csv` has columns: `sample_id`, `signer`, `split`, `label_id`, `label_id_str`, `frames_dir`, `n_frames`.

#### `src/data_prep/build_labels.py`

Reads the Excel file `KARSL-502_Labels.xlsx` and produces two JSON mappings: `label2text.json` (label ID → Arabic text) and `text2label.json` (Arabic text → label ID). It auto-detects which Excel columns hold the numeric ID and the text description using a heuristic that scores columns by how many valid label IDs or non-numeric strings they contain.

#### `src/models/baseline_resnet_lstm.py`

Defines `ResNetLSTMClassifier`, the current baseline model. Takes a batch of video clips `(B, T, 3, H, W)`, passes each frame through a pretrained ResNet18 (with the final FC layer replaced by Identity) to get 512-dim features, feeds the sequence through a 1-layer bidirectional LSTM (hidden=256), takes the last timestep output (512-dim after concatenating both directions), applies dropout, and passes through a linear classifier to produce 502-class logits.

#### `src/train/dataset.py`

Defines `KArSLFramesDataset`, a PyTorch Dataset. For each sample in the data index, it reads the frame image files from disk, uniformly samples `num_frames` frames (default 32), resizes them to `img_size×img_size` (default 224), normalizes with ImageNet mean/std, and returns a `(T, 3, H, W)` float tensor with a 0-indexed label. Handles edge cases like missing frames (blank fallback) and short clips (pads by repeating the last frame).

#### `src/train/trainer.py`

Contains `train_one_epoch()` and `evaluate()` functions. Both iterate over a DataLoader, compute cross-entropy loss and top-1/top-5 accuracy per batch, and return averaged metrics. Training uses AdamW with gradient zeroing via `set_to_none=True`. Evaluation runs under `@torch.no_grad()`. Both display progress bars via tqdm.

#### `src/train/metrics.py`

Single function `topk_accuracy(logits, targets, k)` — computes the fraction of samples where the true label appears in the top-K predicted classes.

#### `src/utils/io.py`

Three small helpers used across the pipeline: `ensure_dir(path)` creates directories recursively, `write_json(path, data)` writes JSON with UTF-8 encoding, `read_env_default(name, default)` reads an environment variable with a fallback.

#### `scripts/phase1_build_index.py`

Entry point for Phase 1. Reads `DATASET_ROOT` and `OUTPUT_DIR` from environment variables, calls `build_data_index()`, saves `data_index.csv`, and prints a validation summary.

#### `scripts/phase2_build_labels.py`

Entry point for Phase 2. Reads `LABELS_XLSX` and `OUTPUT_DIR` from environment variables, calls `build_label_maps()` and `save_label_maps()`, and prints the count plus any missing label IDs.

#### `scripts/phase3_train_baseline.py`

Entry point for Phase 3. Parses CLI arguments (signer filter, epochs, batch size, learning rate, etc.), loads `data_index.csv`, filters by signer if requested, splits train data into train/val (with optional stratification), creates DataLoaders, instantiates the model, and runs the training loop. Every epoch logs metrics to MLflow. Saves the best checkpoint (by validation top-1 accuracy) to disk and registers it in MLflow Model Registry. Finally evaluates on the held-out test set.

### API & Inference (`src/api/`)

#### `src/api/main.py`

FastAPI application entry point. On startup, creates database tables and loads the trained model checkpoint. Exposes `POST /predict/video` (accepts a video file upload) and `POST /predict/frames` (accepts base64-encoded frames from the webcam). Both endpoints decode the input, run inference via `ModelInference`, save the result to prediction history, and return top-K predictions with confidence scores. Also exposes `GET /health` for status checks.

#### `src/api/inference.py`

`ModelInference` class that handles the full serving pipeline: loads the model checkpoint and label map, preprocesses video files or raw frames (decode → resize → ImageNet normalize → uniform temporal sampling → tensor), runs forward pass under `torch.no_grad()`, and converts 0-indexed model outputs back to 1-indexed label IDs with Arabic text.

#### `src/api/auth/`

Full JWT-based authentication system: user registration, login, profile updates, password changes (with current password verification). Uses bcrypt for password hashing, python-jose for JWT tokens, and SQLAlchemy for persistence in PostgreSQL. Prediction history is stored per-user with type, label, confidence, and timestamp.

### Frontend (`frontend/src/`)

React 18 SPA built with Vite and styled with Tailwind CSS. Features:

- **Video Upload** — drag-and-drop or file picker, sends video to `/predict/video`, displays top-K results with confidence bars
- **Webcam Capture** — accesses browser camera, records configurable frame buffers (30–120 frames), sends to `/predict/frames`
- **Authentication** — register, login, change password on profile page, JWT stored in localStorage with Axios interceptors
- **History** — paginated list of past predictions with type, label, confidence, and timestamps
- **Dashboard** — usage statistics and charts (powered by Recharts)
- **Protected Routes** — all main pages require authentication, redirects to login if not authenticated

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (recommended — everything runs in containers)
- The **KArSL dataset** extracted to `data/raw/KArSL/`
- The **label file** at `data/raw/labels/KARSL-502_Labels.xlsx`

### 1. Start all services

```bash
docker compose up -d --build
```

This starts 4 containers:

| Service | Port | Description |
|---------|------|-------------|
| `arsl_frontend` | 3000 | React web app |
| `arsl_api` | 8000 | FastAPI backend |
| `arsl_mlflow` | 5000 | MLflow experiment tracker |
| `arsl_postgres` | 5432 | PostgreSQL database |

### 2. Prepare the data

```bash
# Phase 1: Scan dataset and build the sample index
docker compose exec api python scripts/phase1_build_index.py

# Phase 2: Parse the Excel label file into JSON maps
docker compose exec api python scripts/phase2_build_labels.py
```

### 3. Train the model

```bash
# Quick test (~5 min) — trains on 200 samples for 1 epoch
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --batch_size 32 \
  --max_samples 200 --num_frames 16
```

### 4. Use the app

Open http://localhost:3000, register an account, and start predicting.

---

## Data Preparation Pipeline

### Phase 1: Build Data Index

```bash
docker compose exec api python scripts/phase1_build_index.py
```

**What it does:** Recursively walks `data/raw/KArSL/{signer}/{split}/` directories. For every folder that contains image files (.jpg/.png), it extracts the label ID from the folder name, counts the frames, and records the full path. Produces `outputs/index/data_index.csv`.

**Expected output for a complete dataset:** 75,300 samples (502 classes x 3 signers x 50 repetitions).

### Phase 2: Build Label Maps

```bash
docker compose exec api python scripts/phase2_build_labels.py
```

**What it does:** Reads `KARSL-502_Labels.xlsx`, auto-detects which columns contain the numeric label IDs (1–502) and the Arabic text descriptions, then writes `label2text.json` and `text2label.json` to `outputs/index/`.

---

## Model Training

### Phase 3: Train Baseline

```bash
docker compose exec api python scripts/phase3_train_baseline.py [OPTIONS]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--use_signer` | `all` | Signer filter: `01`, `02`, `03`, or `all` |
| `--epochs` | `10` | Number of training epochs |
| `--batch_size` | `8` | Batch size |
| `--lr` | `3e-4` | Learning rate (AdamW) |
| `--weight_decay` | `1e-4` | Weight decay |
| `--num_frames` | `32` | Frames sampled per video |
| `--img_size` | `224` | Input image resolution |
| `--val_ratio` | `0.1` | Fraction of train set used for validation |
| `--max_samples` | `None` | Limit samples (for quick tests) |
| `--seed` | `42` | Random seed |

**Example configurations:**

```bash
# Single signer, moderate training (~1-2 hours)
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 20 --batch_size 16

# All signers, full training (several hours)
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer all --epochs 30 --batch_size 8
```

**What happens during training:**
1. Loads `data_index.csv`, optionally filters by signer
2. Splits the train partition into train/val (90/10 by default, stratified when using full data)
3. Creates PyTorch DataLoaders with uniform frame sampling
4. Trains a ResNet18 (ImageNet-pretrained) + BiLSTM with cross-entropy loss and AdamW
5. Logs train/val loss, top-1, and top-5 accuracy to MLflow each epoch
6. Saves the best checkpoint (by val top-1) to `artifacts/models/`
7. Evaluates the best checkpoint on the test set
8. Registers the model in MLflow Model Registry

**Monitor training:** Open MLflow at http://localhost:5000 to view experiments, compare runs, and check metrics.

---

## Web Application

### Frontend (http://localhost:3000)

- **Video Upload** — upload .mp4/.avi files, get top-5 predictions with confidence
- **Webcam** — record from browser camera, adjustable buffer length, real-time prediction
- **History** — see all your past predictions with pagination
- **Dashboard** — charts showing usage over time, prediction type breakdown, top predicted signs
- **Profile** — update username/email, change password
- **Auth** — register, login, JWT-based session management

### Running frontend locally (without Docker)

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` for local dev.

---

## API Reference

**Base URL:** `http://localhost:8000` | **Interactive docs:** `http://localhost:8000/docs`

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (returns `model_loaded` status) |

### Auth Endpoints (prefix: `/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | No | Create account, returns JWT |
| `POST` | `/auth/login` | No | Login, returns JWT |
| `GET` | `/auth/me` | Yes | Get current user profile |
| `PUT` | `/auth/me` | Yes | Update username/email |
| `POST` | `/auth/change-password` | Yes | Change password (requires current password) |
| `GET` | `/auth/history` | Yes | Paginated prediction history |

### Prediction Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/predict/video?top_k=5` | Yes | Upload video file, get predictions |
| `POST` | `/predict/frames` | Yes | Send base64 frames (webcam), get predictions |

**Prediction response format:**

```json
{
  "top_prediction": {
    "label_id": "45",
    "text": "مرحبا",
    "confidence": 0.8723
  },
  "top_k_predictions": [
    { "label_id": "45", "text": "مرحبا", "confidence": 0.8723 },
    { "label_id": "12", "text": "شكرا", "confidence": 0.0531 }
  ]
}
```

---

## Current Status

The project has a **working end-to-end pipeline** but the ML model is still at baseline level:

- **Data pipeline** — complete and functional (phase 1 & 2)
- **Baseline model** — ResNet18 + BiLSTM, only quick-tested with ~200 samples for 1 epoch (~6 minutes). Accuracy is very low because the model has barely been trained
- **Web app** — fully functional (video upload, webcam, auth, history, dashboard)
- **Infrastructure** — Docker Compose with Postgres, MLflow, hot-reload dev setup

The real ML training work has not started yet. The current checkpoint is essentially a proof-of-concept that the pipeline runs end-to-end.

---

## Next Steps & Roadmap

### Phase A: Serious Baseline Training

- [ ] Train the current ResNet18 + BiLSTM on **all 3 signers** for **20-30 epochs** with the full dataset
- [ ] Experiment with different `num_frames` values (16, 32, 48) to find the sweet spot
- [ ] Experiment with batch sizes and learning rates — log everything to MLflow and compare
- [ ] Add a **learning rate scheduler** (e.g., CosineAnnealingLR or ReduceLROnPlateau) to the training script
- [ ] Add **data augmentation** to the dataset (random crops, horizontal flips, color jitter, temporal jitter)
- [ ] Evaluate per-class accuracy to find which signs are hardest to classify

### Phase B: Stronger Model Architectures

- [ ] Try **ResNet50** or **EfficientNet-B0** as the CNN backbone (deeper features)
- [ ] Experiment with **Transformer-based temporal modeling** (replace BiLSTM with a temporal Transformer encoder)
- [ ] Try **3D CNNs** like SlowFast, R(2+1)D, or Video Swin Transformer that process spatiotemporal features natively
- [ ] Explore **attention pooling** instead of taking only the last LSTM timestep
- [ ] Add **multi-head temporal attention** over the LSTM outputs

### Phase C: Training Infrastructure Improvements

- [ ] Implement **early stopping** to avoid overfitting and wasting compute
- [ ] Add a **validation loss plateau detector** that automatically reduces LR
- [ ] Add **gradient clipping** for more stable LSTM training
- [ ] Support **mixed-precision training** (fp16) for faster training on GPU
- [ ] Add **checkpoint resumption** so training can be paused and continued
- [ ] Implement **cross-validation** or signer-wise leave-one-out evaluation

### Phase D: Data & Preprocessing

- [ ] Analyze the dataset distribution — check for class imbalance across the 502 signs
- [ ] Implement **weighted sampling** or **class-weighted loss** if imbalance is significant
- [ ] Add **hand/body pose estimation** as an auxiliary input (e.g., MediaPipe landmarks)
- [ ] Explore **optical flow** as an additional input modality for motion information
- [ ] Implement smarter frame sampling (e.g., motion-based sampling instead of uniform)

### Phase E: App & Deployment

- [ ] Add a **model selection** feature in the UI to switch between different trained models
- [ ] Show **per-sign accuracy breakdown** on the dashboard
- [ ] Add **real-time continuous recognition** mode for the webcam (predict every N seconds)
- [ ] Add **confidence threshold** — display "uncertain" if the top prediction confidence is too low
- [ ] Implement model **A/B testing** using MLflow model registry versions
- [ ] Production deployment with HTTPS, proper secrets management, and a reverse proxy

---

## Troubleshooting

### Model not loading (`model_loaded: false`)

The model checkpoint doesn't exist yet. Train it first:

```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --max_samples 200
```

### Out of memory during training

Reduce memory usage:

```bash
--batch_size 4     # Smaller batches
--num_frames 16    # Fewer frames per sample
--max_samples 500  # Fewer total samples
```

### Frontend can't connect to API

```bash
docker compose restart api
curl http://localhost:8000/health    # Verify API is up
```

### Webcam not working

- Grant camera permissions in your browser
- Use Chrome or Edge (best WebRTC support)
- Must be on `localhost` or HTTPS

### Database issues after model changes

If you changed the User model or database schema, recreate the volume:

```bash
docker compose down -v
docker compose up -d --build
```

---

## Docker Commands Reference

```bash
docker compose up -d --build         # Start everything (rebuild if needed)
docker compose down                  # Stop all services
docker compose down -v               # Stop + delete database volume
docker compose logs -f api           # Follow API logs
docker compose logs -f frontend      # Follow frontend logs
docker compose exec api bash         # Shell into API container
docker compose ps                    # Check service status
```
