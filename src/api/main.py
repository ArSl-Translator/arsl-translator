import os
import tempfile
import base64
import numpy as np
import cv2
from typing import List, Optional, Set

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.inference import ModelInference
from src.api.auth.router import router as auth_router
from src.utils.generate_audio import generate_all_audio
from src.api.database.init_db import create_tables
from src.api.database.connection import get_db
from src.api.auth.dependencies import get_current_user
from src.api.auth.history_service import save_prediction
from src.api.models.user import User

app = FastAPI(title="ArSL Translator API", version="0.1.0")

# React dev server will call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",  # For HTML demo
        "null"  # Allows file:// protocol (less secure, for local testing only)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# Serve pre-recorded audio files for sign label pronunciation
_audio_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "audio")
os.makedirs(_audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=_audio_dir), name="audio")

# Global model instance (loaded on startup)
model_inference: Optional[ModelInference] = None


def resolve_model_path() -> Optional[str]:
    """
    Pick a checkpoint for inference: MODEL_PATH if set, else try best.pt, then last.pt
    (last.pt is written every epoch — use when training stopped before best.pt updated).
    """
    candidates: List[str] = []
    env_path = os.environ.get("MODEL_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            "./models/baseline_resnet18_bilstm_best.pt",
            "./models/baseline_resnet18_bilstm_last.pt",
            "./artifacts/models/baseline_resnet18_bilstm_best.pt",
            "./artifacts/models/baseline_resnet18_bilstm_last.pt",
        ]
    )
    seen: Set[str] = set()
    for p in candidates:
        key = os.path.normpath(os.path.abspath(p))
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(p):
            return p
    return None


@app.on_event("startup")
def startup():
    """Initialize database and load model on API startup."""
    global model_inference

    # Create database tables (with retry for postgres startup timing)
    try:
        create_tables()
    except Exception as e:
        print(f"Warning: Could not create database tables: {e}")

    # Generate pronunciation audio files (skips any that already exist)
    try:
        generate_all_audio()
    except Exception as e:
        print(f"Warning: Audio generation failed: {e}")

    model_path = resolve_model_path()
    if not model_path:
        print("Warning: No checkpoint found. Tried MODEL_PATH, then models/ and artifacts/")
        print("   (baseline_resnet18_bilstm_best.pt and baseline_resnet18_bilstm_last.pt)")
        print("   API will start but predictions will fail until a .pt file is available.")
        return

    if os.environ.get("MODEL_PATH") and not os.path.isfile(os.environ["MODEL_PATH"]):
        print(f"Note: MODEL_PATH ({os.environ['MODEL_PATH']}) missing — using {model_path}")

    try:
        model_inference = ModelInference(model_path=model_path)
        print(f"Model loaded successfully from {model_path}")
        print(f"   Device: {model_inference.device}")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("   API will start but predictions will fail.")


@app.get("/health")
def health():
    """Health check endpoint."""
    model_loaded = model_inference is not None
    return {
        "status": "ok",
        "model_loaded": model_loaded
    }


@app.post("/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a video file and get sign language predictions.

    Args:
        file: Video file (mp4, avi, etc.)
        top_k: Number of top predictions to return

    Returns:
        Prediction results with top-k predictions
    """
    if model_inference is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please train the model first."
        )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Run inference
        result = model_inference.predict_video(tmp_path, top_k=top_k)
        save_prediction(db, current_user, "video", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


class FramesRequest(BaseModel):
    """Request model for webcam frames."""
    frames: List[str]  # Base64 encoded images
    top_k: int = 5


@app.post("/predict/frames")
async def predict_frames(
    request: FramesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send multiple frames (e.g., from webcam) and get sign language predictions.

    Args:
        request: JSON with list of base64-encoded frames and top_k

    Returns:
        Prediction results with top-k predictions
    """
    if model_inference is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please train the model first."
        )

    if not request.frames:
        raise HTTPException(status_code=400, detail="No frames provided")

    try:
        # Decode base64 frames
        frames = []
        for idx, frame_b64 in enumerate(request.frames):
            try:
                # Remove data URL prefix if present
                if ',' in frame_b64:
                    frame_b64 = frame_b64.split(',')[1]

                # Remove any whitespace
                frame_b64 = frame_b64.strip()

                # Decode base64
                img_data = base64.b64decode(frame_b64)

                if len(img_data) == 0:
                    raise ValueError(f"Frame {idx}: Empty image data after base64 decode")

                nparr = np.frombuffer(img_data, np.uint8)

                if len(nparr) == 0:
                    raise ValueError(f"Frame {idx}: Empty numpy array")

                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    raise ValueError(f"Frame {idx}: OpenCV failed to decode image (corrupted or invalid format)")

                frames.append(frame)
            except Exception as frame_err:
                raise ValueError(f"Failed to decode frame {idx}/{len(request.frames)}: {str(frame_err)}")

        if len(frames) == 0:
            raise ValueError("No valid frames were decoded")

        # Run inference
        result = model_inference.predict_frames(frames, top_k=request.top_k)
        save_prediction(db, current_user, "frames", result)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
