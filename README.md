# ArSL Translator

ArSL Translator is an assistive Arabic Sign Language communication platform. It combines machine learning, a full-stack web application, experiment tracking, production deployment, and a companion Android app for offline nearby communication.

The platform is built around one practical idea: a deaf or hard-of-hearing user should be able to communicate through text whether they are using AI sign recognition online or a direct phone-to-phone chat when there is no connectivity.

This repository contains the complete merged project. The previous separate `arabsign/` folder is no longer required; its model-serving logic, documentation, and checkpoint integration now live inside this `arsl-translator/` project.

## What This Project Demonstrates

This project intentionally combines two technical themes:

| Theme | What the project demonstrates |
|---|---|
| AI for accessibility | Arabic sign recognition, Arabic text output, model selection, confidence display, and prediction history |
| Distributed systems | HTTP client/server inference, containerized services, PostgreSQL persistence, MLflow tracking, Bluetooth peer-to-peer sockets, background listener threads, and binary transfer |

The final system is not just a notebook or one trained model. It is a deployable platform with:

- React web frontend.
- FastAPI inference backend.
- PostgreSQL database.
- MLflow experiment tracking.
- Local open-source generative assistant through Ollama.
- Docker and Docker Compose deployment.
- Caddy HTTPS reverse proxy.
- GitHub Actions CI/CD deployment.
- Native Android Bluetooth offline chat app.

## Current Status

| Component | Status |
|---|---|
| Web frontend | Working |
| FastAPI backend | Working |
| Authentication and prediction history | Working |
| KArSL MediaPipe model | Working when `models/karsl_mediapipe_bilstm_best.pt` exists |
| ArabSign model | Working when `models/arabsign_best_model.pt` exists |
| Raw-frame KArSL baseline | Implemented as an experimental baseline, not currently served unless a checkpoint is provided |
| MLflow | Available locally and in production deployment |
| Assistive Message Studio | Optional AI writing assistant for clear messages, simplification, phrasebooks, and quick replies |
| Android offline chat APK | Buildable and downloadable from the website |
| Production deployment | Dockerized for a GCP VM and domain deployment |

## High-Level Architecture

```text
User Browser
  |
  | HTTPS
  v
Caddy Reverse Proxy
  |
  +-- /                  -> React frontend served by Nginx
  +-- /api/*             -> FastAPI backend
  +-- /mlflow*           -> MLflow tracking UI
  |
  v
Docker Network
  |
  +-- frontend container
  +-- api container
  +-- postgres container
  +-- mlflow container
  +-- ollama container

FastAPI Backend
  |
  +-- model registry
  |     +-- karsl_mediapipe
  |     +-- arabsign
  |     +-- karsl raw-frame baseline, optional
  |
  +-- prediction endpoints
  +-- auth endpoints
  +-- prediction history
  +-- audio endpoint
  +-- assistive writing endpoint
  |
  +-- mounted model checkpoints
  +-- mounted generated label maps

Android Offline Chat App
  |
  +-- Bluetooth Classic discovery and pairing
  +-- RFCOMM server/client sockets
  +-- background read thread
  +-- framed text and media transfer
  +-- Room local database
```

## Repository Layout

```text
arsl-translator/
  frontend/                         React + Vite web application
  src/api/                          FastAPI application
    main.py                         API routes and model registry
    inference.py                    Raw-frame KArSL inference adapter
    karsl_mediapipe_inference.py    Landmark-based KArSL inference adapter
    arabsign_inference.py           ArabSign sequence-to-sequence inference adapter
    auth/                           JWT auth, user flows, history service
    database/                       SQLAlchemy database connection and table setup
    models/                         SQLAlchemy ORM models
  src/models/
    baseline_resnet_lstm.py         Raw-frame ResNet18 + BiLSTM classifier
    landmark_lstm.py                Landmark BiLSTM classifier
  src/train/                        Dataset and training utilities
  scripts/
    phase1_build_index.py           Raw KArSL dataset indexing
    phase2_build_labels.py          Label map generation
    phase3_train_baseline.py        Raw-frame baseline training
    phase3_prepare_mediapipe_csv.py MediaPipe CSV preparation
    phase3_train_mediapipe_csv.py   KArSL MediaPipe training
    mlflow_log_current_models.py    Logs current served checkpoints to MLflow
    arabsign/                       Standalone ArabSign training/demo scripts
  offline-chat-android/             Native Android Bluetooth chat app
  deploy/                           Production deployment files
  models/                           Local model checkpoints, ignored by Git
  outputs/                          Generated indexes and label maps, ignored by Git
  artifacts/                        Training outputs, ignored by Git
  mlruns/                           MLflow tracking data, ignored by Git
```

## Web Application

The web app is built with React and Vite. It is the main user-facing interface for sign recognition and platform access.

### Main Capabilities

| Feature | Description |
|---|---|
| Video upload | Upload a sign video and send it to the backend for model inference |
| Webcam capture | Capture browser frames and send a sampled frame sequence to the backend |
| Recognition engine selector | Select between available model backends based on `/health` |
| Prediction result panel | Shows top prediction, confidence, label ID, and top-k alternatives |
| Authentication | Register, login, JWT-based protected pages |
| Prediction history | Saves predictions per authenticated user |
| Dashboard | Shows prediction usage summaries |
| Offline chat page | Presents the Android app, APK download, and two-phone demo link |
| Assistive Message Studio | Optional AI support for writing clearer messages and simplifying text |

### Frontend Model Selection

The frontend uses `/health` to discover which recognition engines are actually loaded. The selector currently supports:

| Engine key | User-facing meaning | Status behavior |
|---|---|---|
| `karsl_mediapipe` | KArSL isolated-sign recognition | Ready when `models/karsl_mediapipe_bilstm_best.pt` is mounted |
| `arabsign` | ArabSign phrase translation | Ready when `models/arabsign_best_model.pt` is mounted |
| `karsl` | Raw-frame image-sequence KArSL recognition | Disabled unless a raw-frame checkpoint exists |

The frontend sends the selected model key to the API:

```text
POST /api/predict/video?model=karsl_mediapipe
POST /api/predict/video?model=arabsign
POST /api/predict/frames
```

For webcam prediction, the body includes the selected model:

```json
{
  "model": "karsl_mediapipe",
  "top_k": 5,
  "frames": ["data:image/jpeg;base64,..."]
}
```

## Assistive Message Studio

Assistive Message Studio is the optional generative AI layer. It is intentionally separate from sign prediction: it does not change model outputs or claim to improve recognition accuracy. Instead, it helps people communicate more clearly through text.

The feature supports four communication tasks:

| Mode | Direction | Purpose |
|---|---|---|
| `deaf_to_hearing` | Deaf user -> hearing person | Turn a rough or short idea into a clear, natural sentence |
| `hearing_to_deaf` | Hearing person -> deaf user | Simplify a longer message into short, direct wording |
| `phrasebook` | Context -> ready phrases | Generate useful phrases for a clinic, classroom, public service, emergency, or general situation |
| `smart_replies` | Context -> quick replies | Suggest short replies that can be sent during a conversation |

The mobile app still works fully offline for Bluetooth chat. The AI writing assistant is an optional online feature that calls the deployed ArSL API, which then calls a local open-source model running on the VM through Ollama.

Runtime flow:

```text
Android app
  -> POST /api/ai/assist
  -> FastAPI prompt builder
  -> Ollama local model, default qwen2.5:1.5b
  -> generated communication text
  -> editable/copyable suggestion in the app
```

Endpoint:

```text
POST /api/ai/assist
```

Request:

```json
{
  "text": "I did not understand the doctor",
  "mode": "hearing_to_deaf",
  "context": "clinic",
  "language": "ar"
}
```

Response:

```json
{
  "mode": "hearing_to_deaf",
  "context": "clinic",
  "output": "لم أفهم. اشرح لي بكلمات بسيطة من فضلك.",
  "model": "qwen2.5:1.5b",
  "source": "ollama"
}
```

If Ollama is unavailable, the endpoint returns a safe fallback response instead of breaking the app. This keeps the mobile experience usable even before the VM model is downloaded.

## FastAPI Backend

The backend is the central inference and application API.

### Main Responsibilities

- Load available model checkpoints at startup.
- Expose health information for frontend model availability.
- Accept video uploads and webcam frame sequences.
- Route each prediction request to the selected model adapter.
- Save prediction history for authenticated users.
- Serve authentication endpoints.
- Serve generated audio pronunciation files when available.
- Serve optional assistive writing requests through a local Ollama model.
- Connect to PostgreSQL through SQLAlchemy.

### Model Registry

The backend keeps a runtime model registry:

```text
model_registry = {
  "karsl_mediapipe": KArSLMediaPipeInference(...),
  "arabsign": ArabSignInference(...),
  "karsl": ModelInference(...),              # optional
}
```

Checkpoint paths are resolved from environment variables first and then from common local paths:

```text
KARSL_MEDIAPIPE_MODEL_PATH=/app/models/karsl_mediapipe_bilstm_best.pt
ARABSIGN_MODEL_PATH=/app/models/arabsign_best_model.pt
MODEL_PATH=/app/models/baseline_resnet18_bilstm_last.pt
```

If a checkpoint is missing, that model is simply not loaded. The API remains online and `/health` reports the missing model as unavailable.

### Health Endpoint

```text
GET /api/health
```

Example response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "models": {
    "karsl": {
      "loaded": false,
      "path": null
    },
    "karsl_mediapipe": {
      "loaded": true,
      "path": "/app/models/karsl_mediapipe_bilstm_best.pt"
    },
    "arabsign": {
      "loaded": true,
      "path": "/app/models/arabsign_best_model.pt"
    }
  },
  "mediapipe_pose_model_available": true,
  "mediapipe_hand_model_available": true
}
```

## Model 1: KArSL MediaPipe Landmark BiLSTM

This is the main KArSL model currently used for isolated sign recognition.

### Purpose

Classify one isolated Arabic sign into one of 502 KArSL classes using pre-extracted landmark sequences instead of raw image frames.

### Why This Route Is Practical

The original raw image/video dataset is large and expensive to move around. The MediaPipe CSV version is much smaller because each sample already contains landmark coordinates. This makes it much more practical on a CPU VM and easier to deploy.

### Dataset Format

The MediaPipe Pose dataset files look like:

```text
data/mediapipe_pose/
  KARSL-502_Labels.xlsx
  KARSL_Labels.txt
  signer01_train.csv
  signer01_test.csv
  signer02_train.csv
  signer02_test.csv
  signer03_train.csv
  signer03_test.csv
```

The CSV files contain:

- `signerID`
- `sign`
- `NoFrames`
- one column per landmark coordinate

Each landmark coordinate cell stores a sequence list, for example all `x` values for `nose_X` across the frames of that sign sample.

The detected training representation for this dataset was:

```text
108 numeric features per frame
= 12 body/neck keypoints x 2 coordinates
+ 21 right-hand keypoints x 2 coordinates
+ 21 left-hand keypoints x 2 coordinates
```

### Preparation Pipeline

`scripts/phase3_prepare_mediapipe_csv.py` converts the original large CSV files into compact per-sample sequence files and a manifest:

```text
CSV row
  -> parse list-valued landmark columns
  -> reconstruct frame sequence
  -> normalize/validate feature dimension
  -> save compact sample file
  -> write row in mediapipe_manifest.csv
```

Dry run:

```bash
PYTHONPATH=. python scripts/phase3_prepare_mediapipe_csv.py \
  --csv_dir ./data/mediapipe_pose \
  --output_dir ./outputs/mediapipe \
  --dry_run
```

Full preparation:

```bash
PYTHONPATH=. python scripts/phase3_prepare_mediapipe_csv.py \
  --csv_dir ./data/mediapipe_pose \
  --output_dir ./outputs/mediapipe
```

### Learning Algorithm

Model file:

```text
src/models/landmark_lstm.py
```

Architecture:

```text
Input landmark sequence
  shape: (batch, time, features)
  example: (B, 64, 108)

LayerNorm over feature dimension
  -> normalizes coordinate feature scale

Bidirectional LSTM
  hidden_size: 256 or 384 depending on run
  layers: 2
  bidirectional: true

Temporal pooling
  mean over time dimension

Classifier head
  Dropout
  Linear(hidden*2 -> hidden)
  ReLU
  Dropout
  Linear(hidden -> 502 classes)
```

Loss and optimizer:

```text
Loss: CrossEntropyLoss
Optimizer: AdamW
Default learning rate: 3e-4
Default weight decay: 1e-4
Metric: top-1 accuracy, top-5 accuracy, loss
```

### Training Commands Used

Initial full training run:

```bash
PYTHONPATH=. python scripts/phase3_train_mediapipe_csv.py \
  --manifest_csv ./outputs/mediapipe/mediapipe_manifest.csv \
  --use_signer all \
  --epochs 15 \
  --batch_size 32 \
  --num_frames 64 \
  --hidden_size 256 \
  --no_mlflow
```

Longer training run:

```bash
PYTHONPATH=. python scripts/phase3_train_mediapipe_csv.py \
  --manifest_csv ./outputs/mediapipe/mediapipe_manifest.csv \
  --use_signer all \
  --epochs 30 \
  --batch_size 32 \
  --num_frames 96 \
  --hidden_size 384 \
  --no_mlflow
```

### Training Results Observed

These are the results observed during the VM training session.

| Run | Important settings | Best/Final validation behavior | Test result |
|---|---|---|---|
| Smoke test | 1 epoch, 1,200 prepared samples | Only used to verify code path | top-1 `0.0402`, top-5 `0.0938`, loss `6.2143` |
| Baseline run | 15 epochs, 64 frames, hidden size 256, batch size 32 | Validation top-1 reached about `0.7863` near epoch 14 | top-1 `0.7814`, top-5 `0.8848`, loss `1.0234` |
| Longer run | 30 epochs, 96 frames, hidden size 384, batch size 32 | Validation top-1 peaked around `0.7891` near epoch 26, then overfitting increased | top-1 `0.7829`, top-5 `0.8810`, loss `1.3849` |

Interpretation:

- The 15 epoch model was already strong and stable.
- The 30 epoch model improved training accuracy but did not meaningfully improve test accuracy.
- Validation loss increased late in the 30 epoch run, which suggests overfitting.
- The landmark route is useful because it gives strong performance without needing the original raw image dataset.

### Inference Runtime

File:

```text
src/api/karsl_mediapipe_inference.py
```

Runtime flow:

```text
Video/webcam frame
  -> optional horizontal mirror
  -> MediaPipe Pose Landmarker
  -> MediaPipe Hand Landmarker
  -> reconstruct 108-value feature vector
  -> uniform sample/pad to fixed sequence length
  -> per-sample normalization
  -> LandmarkBiLSTMClassifier
  -> softmax top-k labels
  -> map label ID to Arabic text using outputs/index/label2text.json
```

Important environment variables:

```text
KARSL_MEDIAPIPE_MODEL_PATH=/app/models/karsl_mediapipe_bilstm_best.pt
MEDIAPIPE_MODEL_PATH=/app/mediapipe_models/pose_landmarker_full.task
HAND_LANDMARKER_MODEL_PATH=/app/mediapipe_models/hand_landmarker.task
KARSL_MEDIAPIPE_MIRROR_INPUT=true
KARSL_MEDIAPIPE_SWAP_HANDS=false
```

`KARSL_MEDIAPIPE_MIRROR_INPUT=true` was kept because webcam/front-camera recordings are often horizontally flipped compared with the dataset orientation. In testing, manually mirrored input improved confidence for the sample video, so mirroring became the default runtime behavior.

## Model 2: ArabSign GRU Attention Translator

This model is the migrated ArabSign sentence/phrase translation path.

### Purpose

Translate a sequence of pose landmarks into Arabic text. Unlike KArSL classification, this is a sequence-to-sequence translation problem rather than a single-class classification problem.

### Model File

```text
src/api/arabsign_inference.py
```

Checkpoint:

```text
models/arabsign_best_model.pt
```

### Input Representation

ArabSign uses:

```text
25 pose landmarks x 3 coordinates = 75 features per frame
```

Runtime extraction:

```text
Video/webcam frame
  -> MediaPipe Pose Landmarker
  -> 25 body pose landmarks
  -> flatten x/y/z coordinates
  -> sequence tensor (T, 75)
```

Minimum detected frames:

```text
MIN_FRAMES = 30
```

If fewer than 30 pose frames are detected, inference raises an error because the sequence is too short for reliable translation.

### Learning Algorithm

ArabSign is an encoder-decoder sequence model with attention.

Architecture:

```text
Input sequence
  shape: (T, 75)

Encoder
  Bidirectional GRU
  combines forward and backward hidden states
  projects hidden state into decoder hidden dimension

Attention
  additive attention over encoder time steps
  learns which input frames matter for each generated token

Decoder
  token embedding
  GRU decoder
  attention context vector
  linear projection to vocabulary
  log softmax over output tokens

Output
  generated Arabic token sequence until <EOS>
```

The model uses special tokens:

```text
<PAD>, <SOS>, <EOS>
```

### Inference Flow

```text
Extract pose features
  -> tensor (T, 75)
  -> encoder produces contextual frame states
  -> decoder starts with <SOS>
  -> attention selects relevant frame information
  -> greedy token decoding
  -> stop at <EOS> or max length
  -> join generated tokens into Arabic text
```

### Reported ArabSign Metrics

The migrated ArabSign notes reported:

| Metric | Value |
|---|---:|
| Test WER | `0.26%` |
| BLEU-1 | `0.997` |
| BLEU-2 | `0.996` |
| Train samples | `7,492` |
| Test samples | `1,843` |
| Sentence classes | `50 Arabic sentences` |

These numbers are from the migrated ArabSign training notes. For a final academic report, re-running evaluation from the exact checkpoint and dataset is recommended if the professor requires fully reproducible metrics.

## Model 3: Raw-Frame KArSL ResNet18 + BiLSTM Baseline

This model path is implemented but not currently the main production model.

### Purpose

Classify one isolated KArSL sign directly from RGB video frames or image-frame folders.

This was the original KArSL approach before the MediaPipe CSV version became the more practical deployment route.

### Why It Is Not Currently Served

The raw-frame baseline needs the original image/video dataset, which is much larger than the MediaPipe CSV dataset. Training it well is more expensive because every batch passes image frames through a CNN backbone.

The current project keeps this route because it is technically valuable:

- It demonstrates raw visual deep learning.
- It gives an experimental baseline in MLflow.
- It shows why the landmark route is better for deployment on limited infrastructure.

### Model File

```text
src/models/baseline_resnet_lstm.py
```

### Learning Algorithm

Architecture:

```text
Input video clip
  shape: (batch, time, 3, height, width)

Frame encoder
  ResNet18 CNN
  removes final FC layer
  outputs 512-dimensional feature vector per frame

Temporal model
  Bidirectional LSTM over frame feature sequence

Classifier
  use final timestep
  dropout
  linear layer to 502 KArSL classes
```

Loss and optimizer in the training script:

```text
Loss: CrossEntropyLoss
Optimizer: AdamW
Metrics: top-1 accuracy, top-5 accuracy, loss
```

### Training Pipeline

Prepare raw KArSL index and labels:

```bash
docker compose exec api python scripts/phase1_build_index.py
docker compose exec api python scripts/phase2_build_labels.py
```

Smoke training:

```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer 01 \
  --epochs 1 \
  --batch_size 16 \
  --max_samples 200 \
  --num_frames 16
```

Full training starting point:

```bash
docker compose exec api python scripts/phase3_train_baseline.py \
  --use_signer all \
  --epochs 30 \
  --batch_size 8 \
  --num_frames 32
```

### MLflow Experiments

Existing MLflow runs show this route as `resnet18_bilstm`. Some runs completed and some failed or were interrupted. There is currently no final production checkpoint mounted for this route, so the frontend correctly shows it as unavailable unless a checkpoint is added.

Recommended positioning:

```text
Raw-frame KArSL is an implemented experimental baseline.
KArSL MediaPipe is the selected production KArSL route because it is lighter, faster, and already trained.
```

## Model Comparison

| Model | Problem type | Input | Algorithm | Current role |
|---|---|---|---|---|
| KArSL MediaPipe BiLSTM | 502-class isolated sign classification | 108 landmark coordinates per frame | LayerNorm + BiLSTM + MLP classifier | Main KArSL production model |
| ArabSign GRU Attention | Arabic phrase generation | 75 pose features per frame | BiGRU encoder + attention GRU decoder | Phrase translation model |
| Raw-frame KArSL ResNet18 + BiLSTM | 502-class isolated sign classification | RGB frame sequence | ResNet18 frame encoder + BiLSTM | Experimental baseline |

## MLflow Experiment Tracking

MLflow is included to show experiment history and current model tracking.

### Local MLflow

Start the development stack:

```bash
docker compose up -d --build
```

Open:

```text
http://localhost:5000
```

### Production MLflow

Production exposes MLflow through Caddy:

```text
https://arsl.hadighazi.com/mlflow
```

The production compose file runs:

```text
mlflow server
  --host 0.0.0.0
  --port 5000
  --backend-store-uri sqlite:////mlflow/mlflow.db
  --artifacts-destination /mlflow/artifacts
  --static-prefix /mlflow
```

Tracking data is stored on the VM:

```text
~/arsl-translator/mlruns/
```

### Logging Current Served Models

After `karsl_mediapipe_bilstm_best.pt` and `arabsign_best_model.pt` exist in `models/`, log them:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec api \
  python scripts/mlflow_log_current_models.py --tracking_uri http://mlflow:5000
```

If you only want metadata without copying the large checkpoint files into MLflow artifacts:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec api \
  python scripts/mlflow_log_current_models.py --tracking_uri http://mlflow:5000 --skip_artifacts
```

The script logs:

- model key
- model name
- checkpoint file name
- checkpoint size
- checkpoint SHA-256
- checkpoint metadata such as epoch, input dimension, hidden size, and validation metric when available

## Android Offline Chat App

The Android app is a companion assistive communication tool. It is not dependent on the AI backend and does not need internet connectivity.

Project path:

```text
offline-chat-android/
```

APK download path in the website:

```text
frontend/public/downloads/accessible-chat.apk
```

Demo link on the website:

```text
https://canva.link/66ztb1hat1s22fr
```

### User Scenario

Two people are physically near each other:

1. The assisted person opens the app.
2. The helper opens the app on a second Android phone.
3. One phone acts as the Bluetooth host.
4. The other phone connects as the Bluetooth client.
5. They exchange text and media without Wi-Fi, mobile data, or a server.

### Technical Stack

| Layer | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose |
| Architecture | ViewModel + StateFlow |
| Local database | Room over SQLite |
| Communication | Bluetooth Classic RFCOMM sockets |
| Background work | Java/Kotlin threads for blocking socket reads |
| Media | Android camera, file picker, audio recorder, FileProvider |
| Packaging | Signed Android APK |

### Distributed Systems Concepts

| Concept | Android implementation |
|---|---|
| Peer-to-peer system | Phones communicate directly without a central server |
| Client/server roles | One phone listens with a Bluetooth server socket; the other connects with a client socket |
| Socket programming | RFCOMM socket input/output streams are used for all data |
| Threading | A background listener thread blocks on reads while the UI remains responsive |
| Message framing | Each payload begins with a type byte and length fields |
| Binary transfer | Media files are transferred in chunks over the socket stream |
| Fault handling | Disconnection closes streams and updates connection state |
| Local persistence | Room stores conversations and chat messages |
| Per-peer state | Conversation IDs are based on Bluetooth device addresses |

### Bluetooth Connection Flow

```text
Phone A: assisted user
  -> starts BluetoothServer
  -> listenUsingRfcommWithServiceRecord(...)
  -> blocks on accept()
  -> creates BluetoothDataTransfer after socket is accepted

Phone B: helper
  -> scans or lists paired devices
  -> selects Phone A
  -> createRfcommSocketToServiceRecord(...)
  -> socket.connect()
  -> creates BluetoothDataTransfer after connection succeeds

Both phones
  -> start background listening thread
  -> send and receive framed messages
  -> insert messages into Room database
  -> update Compose UI from ViewModel state
```

### Message Framing Protocol

File:

```text
offline-chat-android/app/src/main/java/com/healthcare/offlinechat/bluetooth/BluetoothDataTransfer.kt
```

Text message frame:

```text
1 byte   message type = 0x01
4 bytes  UTF-8 byte length
N bytes  UTF-8 message content
```

Media message frame:

```text
1 byte   message type = 0x02
4 bytes  metadata JSON byte length
N bytes  metadata JSON
8 bytes  media byte length
M bytes  media payload streamed in 8192-byte chunks
```

Safety limits in code:

```text
Text payload max check: 10,000,000 bytes
Metadata max check: 1,000,000 bytes
Chunk size: 8192 bytes
```

### Local Data Model

Room entities:

```text
Conversation
  deviceAddress
  deviceName
  lastMessage
  lastMessageTime
  unreadCount

ChatMessage
  conversationId
  content
  senderName
  isFromMe
  messageType
  mediaUri
  mediaFileName
  mediaMimeType
  mediaDuration
  mediaSize
  timestamp
```

This means the app can preserve chat history even after Bluetooth disconnects or the app closes.

### Android Build

Open in Android Studio:

```text
arsl-translator/offline-chat-android
```

Debug build:

```powershell
cd offline-chat-android
.\gradlew.bat assembleDebug
```

Release build:

```powershell
cd offline-chat-android
.\gradlew.bat :app:assembleRelease --no-daemon --console=plain
```

Signing configuration uses:

```text
offline-chat-android/keystore.properties
```

That file is ignored by Git because it contains signing secrets.

## Local Development

### Docker Development Stack

From the repository root:

```bash
docker compose up -d --build
```

Open:

```text
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
Health:   http://localhost:8000/health
MLflow:  http://localhost:5000
```

### Local Checkpoints

Model checkpoints are ignored by Git and should be placed manually:

```text
models/
  karsl_mediapipe_bilstm_best.pt
  arabsign_best_model.pt
  baseline_resnet18_bilstm_last.pt       optional
```

Generated label maps:

```text
outputs/index/
  label2text.json
  text2label.json
```

### Important Environment Variables

```text
DATABASE_URL=postgresql://arsl_user:arsl_password@postgres:5432/arsl_db
JWT_SECRET_KEY=change-me-in-production
MODEL_PATH=/app/models/baseline_resnet18_bilstm_last.pt
KARSL_MEDIAPIPE_MODEL_PATH=/app/models/karsl_mediapipe_bilstm_best.pt
ARABSIGN_MODEL_PATH=/app/models/arabsign_best_model.pt
MEDIAPIPE_MODEL_PATH=/app/mediapipe_models/pose_landmarker_full.task
HAND_LANDMARKER_MODEL_PATH=/app/mediapipe_models/hand_landmarker.task
KARSL_MEDIAPIPE_MIRROR_INPUT=true
MLFLOW_TRACKING_URI=http://mlflow:5000
OLLAMA_URL=http://ollama:11434
ASSISTANT_MODEL=qwen2.5:1.5b
```

## Production Deployment

Production is designed for a single Google Cloud VM.

### Production Services

| Service | Container | Purpose |
|---|---|---|
| `caddy` | `caddy:2.8-alpine` | HTTPS termination and routing |
| `frontend` | Nginx built from React app | Serves the web UI and APK file |
| `api` | Project Dockerfile | FastAPI backend and model inference |
| `postgres` | `postgres:16-alpine` | User and prediction history database |
| `mlflow` | `ghcr.io/mlflow/mlflow:v2.13.0` | Experiment tracking UI and model metadata |
| `ollama` | `ollama/ollama` | Local open-source LLM runtime for Assistive Message Studio |

### Domain Routing

For the domain:

```text
arsl.hadighazi.com
```

Caddy routes:

```text
/api/*   -> api:8000
/mlflow* -> mlflow:5000
/*       -> frontend:80
```

### DNS

Create an A record:

```text
Type: A
Name: arsl
Value: <VM_EXTERNAL_IP>
TTL: 300
```

The VM firewall must allow inbound ports:

```text
80/tcp
443/tcp
```

### Production Environment File

Copy:

```bash
cp .env.production.example .env.production
```

Then edit:

```text
APP_DOMAIN=arsl.hadighazi.com
ACME_EMAIL=<your-email>
POSTGRES_USER=arsl_user
POSTGRES_PASSWORD=<long-random-password>
POSTGRES_DB=arsl_db
JWT_SECRET_KEY=<openssl-rand-hex-32>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
KARSL_MEDIAPIPE_MIRROR_INPUT=true
```

Generate a strong JWT secret:

```bash
openssl rand -hex 32
```

### Production Deployment Command

```bash
cd ~/arsl-translator
bash deploy/deploy.sh
```

The deploy script:

1. Moves local untracked runtime bundles out of the way if needed.
2. Fetches the latest `main`.
3. Checks out and fast-forwards `main`.
4. Verifies `.env.production` exists.
5. Runs Docker Compose production build and restart.
6. Prints service status.

### Install The Local Assistant Model

The Ollama container starts empty. Pull the small open-source assistant model once on the VM:

```bash
cd ~/arsl-translator
docker compose -f docker-compose.prod.yml --env-file .env.production up -d ollama
docker compose -f docker-compose.prod.yml --env-file .env.production exec ollama \
  ollama pull qwen2.5:1.5b
```

If the VM feels too slow, switch to the smaller model:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec ollama \
  ollama pull qwen2.5:0.5b
```

Then set this in `.env.production`:

```text
ASSISTANT_MODEL=qwen2.5:0.5b
```

Finally redeploy:

```bash
bash deploy/deploy.sh
```

## CI/CD With GitHub Actions

Workflow file:

```text
.github/workflows/deploy.yml
```

The workflow runs on:

```text
push to main
manual workflow_dispatch
```

Stages:

```text
verify
  -> checkout
  -> setup Node.js
  -> npm ci
  -> npm run build
  -> docker compose config validation

deploy
  -> SSH into VM
  -> run deploy/deploy.sh
```

Required GitHub repository secrets:

```text
DEPLOY_HOST=<VM external IP>
DEPLOY_USER=hadighazi16112003
DEPLOY_PORT=22
DEPLOY_PATH=/home/hadighazi16112003/arsl-translator
DEPLOY_SSH_KEY=<private deploy key>
```

The matching public key must exist on the VM:

```text
/home/hadighazi16112003/.ssh/authorized_keys
```

## Training On The GCP VM

The KArSL MediaPipe training was run on a CPU VM using `tmux` so that SSH disconnects do not stop the job.

Start a session:

```bash
tmux new -s karsl-better
```

Detach:

```text
Ctrl+B, then D
```

Reattach:

```bash
tmux attach -t karsl-better
```

Recommended current KArSL MediaPipe training command:

```bash
cd ~/arsl-translator
source .venv/bin/activate

PYTHONPATH=. python scripts/phase3_train_mediapipe_csv.py \
  --manifest_csv ./outputs/mediapipe/mediapipe_manifest.csv \
  --use_signer all \
  --epochs 15 \
  --batch_size 32 \
  --num_frames 64 \
  --hidden_size 256
```

Based on the runs already observed, this is a good balance. More epochs and a larger hidden size produced more overfitting without a meaningful test improvement.

## Demo Flow

A strong presentation flow:

1. Open the production website.
2. Show login/register and dashboard.
3. Open `/api/health` to show loaded engines.
4. Upload a video with KArSL MediaPipe selected.
5. Switch to ArabSign if the checkpoint is installed.
6. Open MLflow at `/mlflow` and show `serving_models`.
7. Explain the raw-frame KArSL baseline as an experimental branch.
8. Open the Offline Chat page.
9. Show the APK download and two-phone demo link.
10. Run the Android app on two phones and explain Bluetooth server/client roles, socket streams, background threads, and binary transfer.

## Troubleshooting

### `arabsign.loaded=false`

The checkpoint is missing from the VM:

```bash
ls -lh ~/arsl-translator/models/arabsign_best_model.pt
```

Copy it to:

```text
~/arsl-translator/models/arabsign_best_model.pt
```

Then redeploy:

```bash
cd ~/arsl-translator
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### `karsl_mediapipe.loaded=false`

Check:

```bash
ls -lh ~/arsl-translator/models/karsl_mediapipe_bilstm_best.pt
```

Also check that the label map exists:

```bash
ls -lh ~/arsl-translator/outputs/index/label2text.json
```

### Prediction history insert fails

The code compacts long prediction type names before inserting. If the database was created with older schema definitions, restart the API after pulling the latest code:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production restart api
```

### MediaPipe model missing

Rebuild the API image. The Dockerfile downloads the task files:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production build api
docker compose -f docker-compose.prod.yml --env-file .env.production up -d api
```

### Webcam does not work on the VM remote desktop

Remote desktop sessions often do not expose the local webcam to the browser. Use video upload for VM testing, or open the production site from your local machine where the browser can access your camera.

### Android APK says package conflict

The phone probably still has the USB-debug build installed. Uninstall the old app first, then install the signed APK.

### Bluetooth chat does not connect

- Use two real Android phones.
- Enable Bluetooth on both.
- Pair the phones in Android system settings if discovery fails.
- Keep the host phone open and waiting.
- Restart Bluetooth if Android caches a stale socket.

## Security Notes

Do not commit:

- `.env.production`
- Android keystore files
- `keystore.properties`
- SSH private keys
- model checkpoints
- dataset files
- MLflow runtime data

These are intentionally ignored by `.gitignore`.

## Summary

ArSL Translator is a complete assistive communication platform. It serves two working AI recognition approaches, keeps a third raw-frame baseline as an experimental branch, tracks models with MLflow, deploys through Docker and CI/CD, and includes a native Android Bluetooth app that demonstrates offline peer-to-peer communication through socket programming and local persistence.
