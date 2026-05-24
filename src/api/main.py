import base64
import os
import tempfile
from typing import Dict, List, Optional, Set

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.arabsign_inference import ArabSignInference, mediapipe_model_available
from src.api.auth.dependencies import get_current_user
from src.api.auth.history_service import save_prediction
from src.api.auth.router import router as auth_router
from src.api.database.connection import get_db
from src.api.database.init_db import create_tables
from src.api.inference import ModelInference
from src.api.karsl_mediapipe_inference import (
    HAND_LANDMARKER_MODEL_PATH,
    KArSLMediaPipeInference,
)
from src.api.models.user import User
from src.utils.generate_audio import generate_all_audio

app = FastAPI(title="ArSL Translator API", version="0.2.0")

def _cors_origins() -> List[str]:
    configured = os.environ.get("CORS_ALLOW_ORIGINS", "")
    defaults = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "null",
    ]
    if not configured:
        return defaults
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

_audio_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "audio")
os.makedirs(_audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=_audio_dir), name="audio")

model_registry: Dict[str, object] = {}
model_paths: Dict[str, Optional[str]] = {}


def resolve_karsl_model_path() -> Optional[str]:
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
    return _first_existing(candidates)


def resolve_arabsign_model_path() -> Optional[str]:
    candidates: List[str] = []
    env_path = os.environ.get("ARABSIGN_MODEL_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            "./models/arabsign_best_model.pt",
            "./models/best_model.pt",
            "./artifacts/models/arabsign_best_model.pt",
        ]
    )
    return _first_existing(candidates)


def resolve_karsl_mediapipe_model_path() -> Optional[str]:
    candidates: List[str] = []
    env_path = os.environ.get("KARSL_MEDIAPIPE_MODEL_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            "./models/karsl_mediapipe_bilstm_best.pt",
            "./models/karsl_mediapipe_bilstm_last.pt",
            "./artifacts/models/karsl_mediapipe_bilstm_best.pt",
            "./artifacts/models/karsl_mediapipe_bilstm_last.pt",
        ]
    )
    return _first_existing(candidates)


def _first_existing(candidates: List[str]) -> Optional[str]:
    seen: Set[str] = set()
    for path in candidates:
        key = os.path.normpath(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(path):
            return path
    return None


def normalize_model_name(model: Optional[str]) -> str:
    selected = (model or "karsl").strip().lower()
    aliases = {
        "default": "karsl",
        "arsl": "karsl",
        "baseline": "karsl",
        "mediapipe": "karsl_mediapipe",
        "karsl-mediapipe": "karsl_mediapipe",
        "karsl_pose": "karsl_mediapipe",
        "pose": "karsl_mediapipe",
        "arab-sign": "arabsign",
        "arab_sign": "arabsign",
    }
    selected = aliases.get(selected, selected)
    if selected not in {"karsl", "karsl_mediapipe", "arabsign"}:
        raise HTTPException(status_code=400, detail=f"Unknown model '{model}'")
    return selected


def get_model_or_503(model: Optional[str]):
    selected = normalize_model_name(model)
    inference = model_registry.get(selected)
    if inference is None:
        raise HTTPException(
            status_code=503,
            detail=f"Model '{selected}' is not loaded. Add its checkpoint and restart the API.",
        )
    return selected, inference


@app.on_event("startup")
def startup():
    global model_paths

    try:
        create_tables()
    except Exception as exc:
        print(f"Warning: Could not create database tables: {exc}")

    try:
        generate_all_audio()
    except Exception as exc:
        print(f"Warning: Audio generation failed: {exc}")

    karsl_model_path = resolve_karsl_model_path()
    karsl_mediapipe_model_path = resolve_karsl_mediapipe_model_path()
    arabsign_model_path = resolve_arabsign_model_path()
    model_paths = {
        "karsl": karsl_model_path,
        "karsl_mediapipe": karsl_mediapipe_model_path,
        "arabsign": arabsign_model_path,
    }

    if karsl_model_path:
        try:
            model_registry["karsl"] = ModelInference(model_path=karsl_model_path)
            print(f"KArSL model loaded from {karsl_model_path}")
        except Exception as exc:
            print(f"Error loading KArSL model: {exc}")
    else:
        print("Warning: KArSL checkpoint missing. Train it or set MODEL_PATH.")

    if karsl_mediapipe_model_path:
        try:
            model_registry["karsl_mediapipe"] = KArSLMediaPipeInference(model_path=karsl_mediapipe_model_path)
            print(f"KArSL MediaPipe model loaded from {karsl_mediapipe_model_path}")
        except Exception as exc:
            print(f"Error loading KArSL MediaPipe model: {exc}")
    else:
        print("Warning: KArSL MediaPipe checkpoint missing. Set KARSL_MEDIAPIPE_MODEL_PATH or place models/karsl_mediapipe_bilstm_best.pt.")

    if arabsign_model_path:
        try:
            model_registry["arabsign"] = ArabSignInference(model_path=arabsign_model_path)
            print(f"ArabSign model loaded from {arabsign_model_path}")
        except Exception as exc:
            print(f"Error loading ArabSign model: {exc}")
    else:
        print("Warning: ArabSign checkpoint missing. Set ARABSIGN_MODEL_PATH or place models/arabsign_best_model.pt.")


@app.get("/health")
def health():
    models = {
        name: {
            "loaded": name in model_registry,
            "path": path,
        }
        for name, path in model_paths.items()
    }
    return {
        "status": "ok",
        "model_loaded": bool(model_registry),
        "models": models,
        "mediapipe_pose_model_available": mediapipe_model_available(),
        "mediapipe_hand_model_available": os.path.isfile(HAND_LANDMARKER_MODEL_PATH),
    }


@app.post("/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    top_k: int = 5,
    model: str = "karsl",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected_model, inference = get_model_or_503(model)

    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = inference.predict_video(tmp_path, top_k=top_k)
        save_prediction(db, current_user, f"video:{selected_model}", result)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


class FramesRequest(BaseModel):
    frames: List[str]
    top_k: int = 5
    model: str = "karsl"


@app.post("/predict/frames")
async def predict_frames(
    request: FramesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected_model, inference = get_model_or_503(request.model)

    if not request.frames:
        raise HTTPException(status_code=400, detail="No frames provided")

    try:
        frames = [_decode_frame(frame_b64, idx, len(request.frames)) for idx, frame_b64 in enumerate(request.frames)]
        result = inference.predict_frames(frames, top_k=request.top_k)
        save_prediction(db, current_user, f"frames:{selected_model}", result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")


def _decode_frame(frame_b64: str, idx: int, total: int) -> np.ndarray:
    try:
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]

        img_data = base64.b64decode(frame_b64.strip())
        if not img_data:
            raise ValueError("Empty image data after base64 decode")

        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("OpenCV failed to decode image")
        return frame
    except Exception as exc:
        raise ValueError(f"Failed to decode frame {idx}/{total}: {exc}")
