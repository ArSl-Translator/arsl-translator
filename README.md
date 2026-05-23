# ArSL Translator

An assistive Arabic Sign Language communication platform that combines AI-based sign recognition, a full-stack web application, and a companion offline Android chat app built around Bluetooth socket programming.

The project is designed for a university demo that connects two ideas:

- **AI for accessibility:** translating Arabic sign language input into readable text.
- **Distributed systems:** client/server communication, peer-to-peer Bluetooth networking, socket streams, background listening threads, binary transfer, and local persistence.

Everything needed for the merged project is inside this `arsl-translator/` folder. The old sibling `arabsign/` folder is no longer required.

## Platform Overview

This project contains three major parts:

| Component | Purpose | Status |
|---|---|---:|
| React + FastAPI web app | Upload videos or use webcam frames, select a model, view predictions, history, dashboard, and audio pronunciation | Working |
| ArabSign pose translator | Trained GRU + attention model served inside the main API | Working if `models/arabsign_best_model.pt` exists |
| KArSL classifier pipeline | ResNet18 + BiLSTM training and inference pipeline for 502 KArSL classes | Pipeline ready; needs serious GPU training |
| Android offline chat | Nearby no-internet communication over Bluetooth sockets for people who cannot speak/hear easily | Project scaffold implemented |

## Why This Is More Than A Model Demo

The application is intentionally structured as a small assistive communication ecosystem:

- The **web platform** demonstrates AI inference, user authentication, prediction history, model selection, and experiment tracking.
- The **model layer** supports two different approaches: pose-sequence translation and raw-frame classification.
- The **mobile app** demonstrates distributed-systems concepts through Bluetooth server/client roles, socket-based peer-to-peer communication, threading, binary media transfer, and local per-device conversations.

## Architecture

```text
React Frontend
  - Video upload
  - Webcam capture
  - Model selector
  - Auth, history, dashboard
  - Offline Chat info page
        |
        | HTTP
        v
FastAPI Backend
  - JWT authentication
  - Prediction endpoints
  - Audio pronunciation files
  - Model registry
        |
        +--> ArabSign GRU + Attention pose translator
        |
        +--> KArSL ResNet18 + BiLSTM classifier
        |
        +--> PostgreSQL prediction history
        |
        +--> MLflow experiment tracking

Android Offline Chat App
  - Bluetooth server/client roles
  - RFCOMM socket streams
  - Background listening thread
  - Text and binary media transfer
  - Room local database
  - Per-device conversation history
```

## Model Approaches

The frontend exposes both approaches through one model selector.

| Option | What it does | Input | Current status |
|---|---|---|---:|
| `arabsign` | Translates pose landmark sequences into Arabic text using a trained GRU encoder-decoder with attention | Video/webcam frames converted to `(T, 75)` pose features using MediaPipe | Ready for demo |
| `karsl` | Classifies one of 502 KArSL signs using ResNet18 frame features and a BiLSTM temporal model | Raw RGB video frames | Training pipeline ready |

Prediction endpoints:

```text
POST /predict/video?model=arabsign
POST /predict/video?model=karsl
POST /predict/frames
```

For `/predict/frames`, the request body includes:

```json
{
  "model": "arabsign",
  "top_k": 5,
  "frames": ["base64-jpeg-frame", "..."]
}
```

## Web App Features

- **Video Upload:** upload a sign video and receive predictions.
- **Webcam Capture:** record browser webcam frames and send them to the selected model.
- **Model Selector:** switch between `ArabSign pose translator` and `KArSL baseline classifier`.
- **Prediction Results:** confidence scores, top-k predictions, Arabic text display.
- **Audio Pronunciation:** KArSL label audio served through `/audio/{label_id}.wav`.
- **Authentication:** register, login, JWT sessions.
- **History:** predictions saved per user.
- **Dashboard:** usage summaries and charts.
- **Offline Chat Page:** explains the companion Android Bluetooth app and where to build it.

## Offline Android Chat App

The Android app lives in:

```text
offline-chat-android/
```

It is a separate native Android project that can be opened directly in Android Studio.

### What It Does

The app allows a person who cannot speak or hear easily to communicate with someone beside them without internet access.

- One phone chooses **I need assistance** and becomes the Bluetooth host.
- Another phone chooses **I want to help** and connects as the client.
- The two phones exchange messages through Bluetooth Classic RFCOMM sockets.
- Chat history is stored locally with Room.
- Each Bluetooth device has its own conversation, so messages from different people are not mixed.
- The app supports Arabic-first UI and RTL layout.
- The app supports text and media messages: images, camera photos, audio recordings, videos, and files.

### Distributed Systems Concepts Demonstrated

| Concept | Implementation |
|---|---|
| Peer-to-peer communication | Two Android devices communicate directly over Bluetooth |
| Client/server roles | Assisted user hosts with a Bluetooth server socket; helper connects with a client socket |
| Socket programming | RFCOMM socket streams are used for message exchange |
| Threading | Background listener thread waits for incoming socket data |
| Binary transfer | Media files are sent as framed binary payloads with metadata |
| Message framing | The app distinguishes text frames from media frames |
| Fault handling | Connection loss updates app state and closes streams |
| Local persistence | Room database stores conversations and messages |
| Per-peer state | Conversation IDs are based on Bluetooth device addresses |

### Android App Structure

```text
offline-chat-android/
  app/src/main/java/com/arsl/offlinechat/
    MainActivity.kt
    AccessibleChatApplication.kt
    bluetooth/
      BluetoothController.kt
      BluetoothServer.kt
      BluetoothClient.kt
      BluetoothDataTransfer.kt
      BluetoothModels.kt
    data/
      AppDatabase.kt
      Conversation.kt
      ConversationDao.kt
      ChatMessage.kt
      ChatMessageDao.kt
      MessageType.kt
    media/
      MediaHandler.kt
      FileUtils.kt
      AudioRecorder.kt
    ui/
      components/
      screens/
      theme/
    viewmodel/
      ChatViewModel.kt
```

### Android Setup

1. Open Android Studio.
2. Choose **File > Open**.
3. Select:

```text
arsl-translator/offline-chat-android
```

4. Sync Gradle with **File > Sync Project with Gradle Files**.
5. Connect two real Android phones. Bluetooth cannot be tested properly on an emulator.
6. Run the app on Phone A and choose **I need assistance**.
7. Run the app on Phone B and choose **I want to help**.
8. Pair the phones in Android Bluetooth settings if needed.
9. Select Phone A from Phone B and start chatting.

Media transfer over Bluetooth is intentionally capped in code to avoid memory issues. Use small files for a classroom demo.

## Quick Start: Web Platform

From this folder:

```bash
docker compose up -d --build
```

Open:

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- MLflow: http://localhost:5000

Register an account, go to **Video Upload** or **Webcam**, then choose the model from the dropdown.

## Checkpoints

Model files are stored in:

```text
models/
  arabsign_best_model.pt
  baseline_resnet18_bilstm_last.pt
  baseline_resnet18_bilstm_best.pt
```

These `.pt` files are ignored by git because they are large.

Docker Compose uses:

```bash
MODEL_PATH=/app/models/baseline_resnet18_bilstm_last.pt
ARABSIGN_MODEL_PATH=/app/models/arabsign_best_model.pt
MEDIAPIPE_MODEL_PATH=/app/mediapipe_models/pose_landmarker_full.task
```

The Docker image downloads the MediaPipe pose landmarker model during build.

## Project Structure

```text
arsl-translator/
  frontend/                 React + Vite web app
  src/api/                  FastAPI app, auth, history, model serving
    inference.py            KArSL ResNet18 + BiLSTM inference
    arabsign_inference.py   ArabSign GRU + attention inference
  src/models/               KArSL model architecture
  src/train/                Dataset, trainer, metrics
  src/data_prep/            KArSL index and label preparation
  scripts/                  KArSL pipeline scripts
    arabsign/               ArabSign standalone training/demo scripts
  offline-chat-android/     Native Android Bluetooth chat app
  docs/                     Additional model notes
  data/                     Local datasets and generated audio
  models/                   Local checkpoints, not committed
  outputs/                  Generated indexes and label maps
  artifacts/                Training artifacts
  mlruns/                   MLflow tracking data
```

## ArabSign Pose Translator

The ArabSign approach is the current ready-to-demo model.

### Serving Flow

```text
Video/Webcam frames
  -> MediaPipe pose detection
  -> 25 landmarks x 3 coordinates
  -> sequence tensor `(T, 75)`
  -> BiGRU encoder
  -> attention decoder
  -> Arabic text
```

### Files

```text
models/arabsign_best_model.pt
src/api/arabsign_inference.py
scripts/arabsign/train_arabsign.py
scripts/arabsign/demo_live.py
scripts/arabsign/demo_video.py
scripts/arabsign/demo_playback.py
docs/arabsign.md
```

### Original Reported Metrics

| Metric | Value |
|---|---:|
| Test WER | 0.26% |
| BLEU-1 | 0.997 |
| BLEU-2 | 0.996 |
| Train samples | 7,492 |
| Test samples | 1,843 |
| Sentences | 50 Arabic sentences |

These metrics come from the migrated ArabSign training notes. Re-run training/evaluation if you need freshly verified numbers for a report.

## KArSL Training Pipeline

The KArSL approach is a second model path. It uses raw RGB frames and a ResNet18 + BiLSTM classifier for 502 signs.

Expected dataset layout:

```text
data/raw/KArSL/
  01/
  02/
  03/
data/raw/labels/KARSL-502_Labels.xlsx
```

Prepare the data:

```bash
docker compose exec api python scripts/phase1_build_index.py
docker compose exec api python scripts/phase2_build_labels.py
```

Quick smoke test:

```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 --epochs 1 --batch_size 16 --max_samples 200 --num_frames 16
```

Real training starting point:

```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer all --epochs 30 --batch_size 8 --num_frames 32
```

After training, copy the best or latest checkpoint into `models/`:

```bash
cp artifacts/models/baseline_resnet18_bilstm_best.pt models/
```

Restart the API:

```bash
docker compose restart api
```

## Google Colab Training

Use Colab for the easiest GPU workflow.

1. Create a new Colab notebook and select a GPU runtime.
2. Upload this project to Google Drive or clone it from GitHub.
3. Upload/extract the KArSL dataset to Drive, for example:

```text
/content/drive/MyDrive/arsl/data/raw/KArSL
/content/drive/MyDrive/arsl/data/raw/labels/KARSL-502_Labels.xlsx
```

4. Install dependencies:

```bash
!pip install -r requirements.base.txt -r requirements.txt
```

5. Point the scripts at Drive paths:

```bash
%env DATASET_ROOT=/content/drive/MyDrive/arsl/data/raw/KArSL
%env LABELS_XLSX=/content/drive/MyDrive/arsl/data/raw/labels/KARSL-502_Labels.xlsx
%env OUTPUT_DIR=/content/drive/MyDrive/arsl/outputs/index
```

6. Build index and labels:

```bash
!python scripts/phase1_build_index.py
!python scripts/phase2_build_labels.py
```

7. Train:

```bash
!python scripts/phase3_train_baseline.py \
  --use_signer all \
  --epochs 30 \
  --batch_size 8 \
  --num_frames 32
```

8. Save the checkpoint:

```bash
!mkdir -p /content/drive/MyDrive/arsl/models
!cp artifacts/models/baseline_resnet18_bilstm_best.pt /content/drive/MyDrive/arsl/models/
```

If Colab runs out of memory, reduce `--batch_size` to `4` or `2`, or reduce `--num_frames` to `16`.

## Google Cloud GPU VM Training

Use Google Cloud when you need longer training sessions than Colab allows.

Recommended starting point:

- Machine: `g2-standard-8` or `n1-standard-8`
- GPU: NVIDIA L4, T4, or better
- Boot disk: 100GB+
- Image: Deep Learning VM with PyTorch, or Ubuntu plus NVIDIA drivers

Setup:

```bash
git clone <your-repo-url> arsl-translator
cd arsl-translator

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.base.txt -r requirements.txt
```

Confirm CUDA:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Prepare and train:

```bash
export DATASET_ROOT=$PWD/data/raw/KArSL
export LABELS_XLSX=$PWD/data/raw/labels/KARSL-502_Labels.xlsx
export OUTPUT_DIR=$PWD/outputs/index

python scripts/phase1_build_index.py
python scripts/phase2_build_labels.py

tmux new -s arsl-train
python scripts/phase3_train_baseline.py \
  --use_signer all \
  --epochs 30 \
  --batch_size 8 \
  --num_frames 32
```

Detach from `tmux` with `Ctrl+B`, then `D`. Reattach with:

```bash
tmux attach -t arsl-train
```

## Demo Script For Presentation

1. Start Docker Compose.
2. Open the web app and log in.
3. Show `/health` to prove which models are loaded.
4. Use **ArabSign pose translator** for the trained-model demo.
5. Show **KArSL baseline classifier** in the dropdown and explain it as the second training pipeline.
6. Open MLflow to show experiment tracking.
7. Open the **Offline Chat** page in the web app.
8. Open `offline-chat-android/` in Android Studio and run it on two phones.
9. Explain the distributed-systems layer: Bluetooth server/client roles, socket programming, background listener thread, framed binary transfer, and Room persistence.

## Troubleshooting

`Model 'karsl' is not loaded`

Train or copy a KArSL checkpoint into `models/baseline_resnet18_bilstm_last.pt` or set `MODEL_PATH`.

`Model 'arabsign' is not loaded`

Make sure `models/arabsign_best_model.pt` exists or set `ARABSIGN_MODEL_PATH`.

`MediaPipe pose model not found`

Rebuild the Docker image:

```bash
docker compose build api
docker compose up -d api
```

`No body detected in video`

Use a clear, front-facing video with the signer visible from upper body to hands. The ArabSign model depends on MediaPipe pose detection.

Out of GPU memory during KArSL training:

```bash
--batch_size 4 --num_frames 16
```

Frontend cannot connect to API:

```bash
docker compose ps
docker compose logs -f api
```

Android Bluetooth connection fails:

- Use two real phones, not emulators.
- Pair the phones in Android Bluetooth settings first.
- Keep the assisted-user phone open on the message/conversation screen.
- Restart Bluetooth on both phones and try again.

Large media transfer is slow:

- This is expected over Bluetooth Classic.
- Use small files for demos.
- For larger videos, a future Wi-Fi Direct mode would be more appropriate.
