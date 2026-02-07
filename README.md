# 🤟 ArSL Translator

**Arabic Sign Language Recognition System** using Deep Learning (ResNet18 + BiLSTM) with a modern web interface.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.2-red)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This project implements a complete end-to-end pipeline for Arabic Sign Language (ArSL) recognition:

- **Dataset**: KArSL with 502 sign classes, 3 signers
- **Model**: ResNet18 (CNN) + BiLSTM for video classification
- **Backend**: FastAPI REST API with ML inference
- **Frontend**: React + Vite web application
- **ML Ops**: MLflow for experiment tracking
- **Deployment**: Docker Compose

### What Can It Do?

✅ Upload video files and get sign predictions
✅ Real-time webcam capture with live predictions
✅ Top-K predictions with confidence scores
✅ Beautiful web interface with video/webcam support
✅ Complete training pipeline with experiment tracking

---

## ✨ Features

### 🎥 Video Recognition
- Upload video files (.mp4, .avi, etc.)
- Automatic frame extraction and preprocessing
- Top-K predictions with confidence scores

### 📹 Real-time Webcam
- Live webcam capture in browser
- Configurable frame buffer (30-120 frames)
- Real-time sign language prediction
- Visual recording indicator

### 📊 ML Pipeline
- Automated data preprocessing
- Label mapping from Excel sheets
- Training with MLflow experiment tracking
- Model versioning and artifacts storage
- Support for subset training (quick testing)

### 🚀 Production-Ready
- Dockerized deployment
- REST API with CORS support
- Health checks and monitoring
- Comprehensive error handling
- Modern React frontend

---

## 🏗️ Architecture

### System Overview

```
┌──────────────────┐      ┌──────────────────┐      ┌───────────────────┐
│   Frontend       │ ───> │  FastAPI Backend │ ───> │  ML Model         │
│ React + Vite     │      │  (Port 8000)     │      │  ResNet18 + LSTM  │
│ (Port 3000)      │      └──────────────────┘      └───────────────────┘
└──────────────────┘               │
                                   ▼
                          ┌──────────────────┐
                          │   MLflow Server  │
                          │   (Port 5000)    │
                          └──────────────────┘

All services managed by Docker Compose
```

### Model Architecture

```
Input Video (T frames)
    │
    ▼
ResNet18 CNN (per-frame feature extraction)
    │
    ▼
Feature Sequence (T × 512)
    │
    ▼
Bidirectional LSTM (temporal modeling)
    │
    ▼
Fully Connected + Softmax
    │
    ▼
Output (502 classes)
```

---

## 🔧 Prerequisites

**Option 1: Docker (Recommended) - All-in-One**
- Docker & Docker Compose
- That's it! Everything else runs in containers.

**Option 2: Local Installation**
- Python 3.11+
- Node.js 18+
- CUDA-capable GPU (optional, for faster training)

**Dataset Requirements:**
- KArSL dataset in `data/raw/KArSL/`
- Label Excel file in `data/raw/labels/KARSL-502_Labels.xlsx`

---

## 🚀 Quick Start (3 Steps!)

### 1. Clone & Start Everything

```bash
# Clone the repository
git clone https://github.com/yourusername/arsl-translator.git
cd arsl-translator

# Start ALL services (API + MLflow + Frontend) with ONE command!
docker compose up -d
```

✅ That's it! All services are now running:
- **Frontend**: http://localhost:3000 👈 **Start here!**
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MLflow**: http://localhost:5000

### 2. Prepare Data

```bash
# Build data index
docker compose exec api python scripts/phase1_build_index.py

# Build label mappings
docker compose exec api python scripts/phase2_build_labels.py
```

### 3. Train Model (Quick Test)

```bash
# Quick training with 200 samples (~5-10 minutes)
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --batch_size 32 \
  --max_samples 200 --num_frames 16
```

### 🎉 Done!

Open http://localhost:3000 and start recognizing signs!

---

## 📖 Detailed Usage

### Phase 1: Build Data Index

Creates an index of all video samples in the dataset.

```bash
docker compose exec api python scripts/phase1_build_index.py
```

**Output**: `outputs/index/data_index.csv`

### Phase 2: Build Label Maps

Processes the Excel label file and creates JSON mappings.

```bash
docker compose exec api python scripts/phase2_build_labels.py
```

**Outputs**:
- `outputs/index/label2text.json` - Maps label IDs to text
- `outputs/index/text2label.json` - Maps text to label IDs

### Phase 3: Train Model

Train the ResNet18 + BiLSTM model with various configurations.

**Quick Test (5-10 minutes):**
```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --batch_size 32 \
  --max_samples 200 --num_frames 16
```

**Single Signer (1-2 hours):**
```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 20 --batch_size 16
```

**All Signers, Production (several hours):**
```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer all --epochs 30 --batch_size 8
```

**Training Options:**
- `--use_signer` : Signer ID (01, 02, 03, or all) - default: all
- `--epochs` : Number of epochs - default: 10
- `--batch_size` : Batch size - default: 8
- `--lr` : Learning rate - default: 3e-4
- `--num_frames` : Frames per video - default: 32
- `--img_size` : Image size - default: 224
- `--max_samples` : Limit samples for testing - default: None (use all)

**View Training Progress:**
MLflow UI: http://localhost:5000

---

## 📁 Project Structure

```
arsl-translator/
├── frontend/                         # React frontend application
│   ├── src/
│   │   ├── components/              # React components
│   │   │   ├── VideoUpload.jsx      # Video upload interface
│   │   │   ├── WebcamCapture.jsx    # Webcam interface
│   │   │   └── PredictionResults.jsx # Results display
│   │   ├── services/
│   │   │   └── api.js               # API client
│   │   ├── App.jsx                  # Main app
│   │   └── main.jsx                 # Entry point
│   ├── package.json
│   └── vite.config.js
│
├── src/
│   ├── api/
│   │   ├── main.py                  # FastAPI application
│   │   └── inference.py             # ML inference logic
│   ├── data_prep/
│   │   ├── build_index.py           # Dataset indexer
│   │   └── build_labels.py          # Label processor
│   ├── models/
│   │   └── baseline_resnet_lstm.py  # Model architecture
│   ├── train/
│   │   ├── dataset.py               # PyTorch dataset
│   │   └── trainer.py               # Training utilities
│   └── utils/
│       └── io.py                    # I/O utilities
│
├── scripts/
│   ├── phase1_build_index.py        # Phase 1: Build index
│   ├── phase2_build_labels.py       # Phase 2: Process labels
│   └── phase3_train_baseline.py     # Phase 3: Train model
│
├── examples/
│   ├── test_video_upload.py         # Test video upload
│   ├── test_webcam.py               # Test webcam (Python)
│   ├── webcam_web.html              # Test webcam (HTML)
│   └── README.md                    # Examples documentation
│
├── data/
│   ├── raw/
│   │   ├── KArSL/                   # Dataset (not committed)
│   │   └── labels/                  # Label files (not committed)
│   └── processed/                   # Processed data
│
├── outputs/
│   └── index/                       # Generated indices
│
├── artifacts/
│   └── models/                      # Trained models
│
├── mlruns/                          # MLflow experiments
│
├── docker-compose.yml               # Docker services
├── Dockerfile                       # API container
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

---

## 🔌 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

#### 2. Predict from Video
```http
POST /predict/video?top_k=5
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (form-data): Video file
- `top_k` (query): Number of top predictions (default: 5)

**Response:**
```json
{
  "top_prediction": {
    "label_id": "45",
    "text": "مرحبا",
    "confidence": 0.8723
  },
  "top_k_predictions": [
    {
      "label_id": "45",
      "text": "مرحبا",
      "confidence": 0.8723
    },
    ...
  ]
}
```

#### 3. Predict from Frames
```http
POST /predict/frames
Content-Type: application/json
```

**Body:**
```json
{
  "frames": ["base64_image1", "base64_image2", ...],
  "top_k": 5
}
```

**Response:** Same as video prediction

### Interactive API Docs

Visit http://localhost:8000/docs for Swagger UI documentation.

---

## 🎨 Frontend

The frontend is built with **React**, **Vite**, and **Tailwind CSS**.

### Running with Docker (Recommended)

The frontend runs automatically when you start Docker Compose:

```bash
docker compose up -d
```

Available at: http://localhost:3000

### Local Development (Without Docker)

```bash
cd frontend
npm install
npm run dev
```

App available at: http://localhost:3000

### Build for Production

```bash
cd frontend
npm run build
npm run preview
```

### Features

- **Video Upload Tab**: Upload pre-recorded videos for prediction
- **Webcam Tab**: Real-time webcam capture and prediction
- **API Status Indicator**: Shows API and model status
- **Results Display**: Beautiful UI with confidence scores
- **Responsive Design**: Works on desktop and mobile

### Configuration

The frontend is configured via `docker-compose.yml` environment variables. No manual `.env` file needed when using Docker!

For local development outside Docker, create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

---

## 🐳 Docker Compose Commands

All services (Frontend, API, MLflow) are managed together:

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f           # All services
docker compose logs -f api       # API only
docker compose logs -f frontend  # Frontend only

# Stop all services
docker compose down

# Restart a service
docker compose restart api
docker compose restart frontend

# Rebuild and restart
docker compose up -d --build

# Check service status
docker compose ps

# Execute commands in containers
docker compose exec api python scripts/phase1_build_index.py
docker compose exec api bash     # Open shell in API container
```

### Service Details

| Service  | Container Name  | Port | Description |
|----------|----------------|------|-------------|
| frontend | arsl_frontend  | 3000 | React web application |
| api      | arsl_api       | 8000 | FastAPI backend + ML inference |
| mlflow   | arsl_mlflow    | 5000 | MLflow experiment tracking |

---

## 🐛 Troubleshooting

### Model Not Loading

**Problem:** API health shows `model_loaded: false`

**Solution:**
```bash
# Train the model first
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --max_samples 200
```

### CORS Errors

**Problem:** Frontend can't connect to API

**Solution:**
```bash
# Restart API
docker compose restart api

# Check API is running
curl http://localhost:8000/health
```

### Out of Memory During Training

**Solution:**
```bash
# Reduce batch size
--batch_size 4

# Use fewer frames
--num_frames 16

# Limit training samples
--max_samples 500
```

### Slow Training

**Solution:**
- Check GPU: `docker compose exec api python -c "import torch; print(torch.cuda.is_available())"`
- Increase batch size if memory allows
- Use `--max_samples` for quick tests

### Webcam Not Working

**Solution:**
- Grant browser camera permissions
- Use Chrome (recommended)
- Ensure HTTPS or localhost

---

## 📚 Dataset

**KArSL (Korean-Arabic Sign Language) Dataset:**
- 502 sign classes
- 3 professional signers
- Train/test splits included
- Frame sequences extracted from videos

Place dataset at: `data/raw/KArSL/`
Place labels at: `data/raw/labels/KARSL-502_Labels.xlsx`

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- KArSL Dataset creators
- PyTorch and FastAPI communities
- React and Vite teams
- MLflow project

---

**Built with ❤️ for Arabic Sign Language Recognition**

