# ArabSign Model Notes

This project is now self-contained inside `arsl-translator`; the sibling `arabsign/` folder is no longer required for serving or demoing the ArabSign model.

## What Was Merged

- The trained checkpoint is stored at `models/arabsign_best_model.pt`.
- The serving/inference adapter lives in `src/api/arabsign_inference.py`.
- The main FastAPI app loads it when `ARABSIGN_MODEL_PATH` points to the checkpoint.
- The React frontend exposes it through the model selector as `ArabSign pose translator`.
- The standalone training and demo scripts were copied into `scripts/arabsign/`.

## Model Summary

The ArabSign approach uses pose features rather than raw video frames:

- Feature input: `(T, 75)` where each frame has 25 body landmarks with x/y/z coordinates.
- Encoder: Bidirectional GRU.
- Decoder: GRU with Bahdanau-style attention.
- Output: Arabic text sequence.
- Video/webcam inference uses MediaPipe pose detection to create the `(T, 75)` input.

## Original Reported Metrics

| Metric | Value |
|---|---:|
| Test WER | 0.26% |
| BLEU-1 | 0.997 |
| BLEU-2 | 0.996 |
| Train samples | 7,492 |
| Test samples | 1,843 |
| Sentences | 50 Arabic sentences |

## Files

```text
models/arabsign_best_model.pt
src/api/arabsign_inference.py
scripts/arabsign/train_arabsign.py
scripts/arabsign/demo_live.py
scripts/arabsign/demo_video.py
scripts/arabsign/demo_playback.py
```

## Running The Standalone Scripts

Install the project dependencies first:

```bash
pip install -r requirements.base.txt -r requirements.txt
```

Live webcam demo:

```bash
python scripts/arabsign/demo_live.py --model models/arabsign_best_model.pt --source 0
```

Video file demo:

```bash
python scripts/arabsign/demo_video.py --model models/arabsign_best_model.pt --video sample.mp4
```

Skeleton playback demo:

```bash
python scripts/arabsign/demo_playback.py --model models/arabsign_best_model.pt --sample sample.npy --label sample_label.txt
```

## Serving Through The Main App

Docker Compose sets:

```bash
ARABSIGN_MODEL_PATH=/app/models/arabsign_best_model.pt
MEDIAPIPE_MODEL_PATH=/app/mediapipe_models/pose_landmarker_full.task
```

Use the app at `http://localhost:3000`, then choose **ArabSign pose translator** from the model dropdown on Video Upload or Webcam.
