import base64
import os
import re
import tempfile
from typing import Dict, List, Literal, Optional, Set

import cv2
import numpy as np
import requests
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
from src.api.rag_sign_inference import ArabicAlphabetRAGInference, resolve_chroma_index_dir
from src.utils.generate_audio import generate_all_audio

app = FastAPI(title="ArSL Translator API", version="0.3.0")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
ASSISTANT_MODEL = os.environ.get("ASSISTANT_MODEL", "qwen2.5:1.5b")

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_RE = re.compile(r"[A-Za-z]")
CJK_RE = re.compile(r"[\u3400-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


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


def resolve_rag_sign_index_path() -> Optional[str]:
    candidates: List[str] = []
    env_path = os.environ.get("RAG_SIGN_INDEX_DIR")
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            "./models/rag_sign_index",
            "./models/sign_index",
            "./artifacts/rag_sign_index",
            "./artifacts/sign_index",
        ]
    )
    seen: Set[str] = set()
    for path in candidates:
        key = os.path.normpath(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        resolved = resolve_chroma_index_dir(path)
        if resolved:
            return resolved
    return None


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
    selected = (model or "karsl_mediapipe").strip().lower()
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
        "rag": "arsl_rag",
        "sign_rag": "arsl_rag",
        "arabic-rag": "arsl_rag",
        "arabic_rag": "arsl_rag",
        "arabic_alphabet": "arsl_rag",
        "arabic_alphabet_rag": "arsl_rag",
    }
    selected = aliases.get(selected, selected)
    if selected not in {"karsl", "karsl_mediapipe", "arabsign", "arsl_rag"}:
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
    rag_sign_index_path = resolve_rag_sign_index_path()
    model_paths = {
        "karsl": karsl_model_path,
        "karsl_mediapipe": karsl_mediapipe_model_path,
        "arabsign": arabsign_model_path,
        "arsl_rag": rag_sign_index_path,
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
        print("Warning: KArSL MediaPipe checkpoint missing.")

    if arabsign_model_path:
        try:
            model_registry["arabsign"] = ArabSignInference(model_path=arabsign_model_path)
            print(f"ArabSign model loaded from {arabsign_model_path}")
        except Exception as exc:
            print(f"Error loading ArabSign model: {exc}")
    else:
        print("Warning: ArabSign checkpoint missing.")

    if rag_sign_index_path:
        try:
            model_registry["arsl_rag"] = ArabicAlphabetRAGInference(index_dir=rag_sign_index_path)
            print(f"Arabic alphabet RAG model loaded from {rag_sign_index_path}")
        except Exception as exc:
            print(f"Error loading Arabic alphabet RAG model: {exc}")
    else:
        print("Warning: Arabic alphabet RAG index missing.")


@app.get("/health")
def health():
    models = {
        name: {"loaded": name in model_registry, "path": path}
        for name, path in model_paths.items()
    }
    return {
        "status": "ok",
        "model_loaded": bool(model_registry),
        "models": models,
        "mediapipe_pose_model_available": mediapipe_model_available(),
        "mediapipe_hand_model_available": os.path.isfile(HAND_LANDMARKER_MODEL_PATH),
        "assistant": {"model": ASSISTANT_MODEL, "url": OLLAMA_URL},
    }


@app.post("/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    top_k: int = 5,
    model: str = "karsl_mediapipe",
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
    model: str = "karsl_mediapipe"


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
        frames = [
            _decode_frame(frame_b64, idx, len(request.frames))
            for idx, frame_b64 in enumerate(request.frames)
        ]
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


# ─────────────────────────────────────────────
# AI Assistant
# ─────────────────────────────────────────────

AssistantMode = Literal["deaf_to_hearing", "hearing_to_deaf", "suggestions"]


class AssistRequest(BaseModel):
    text: str = ""
    mode: AssistantMode = "deaf_to_hearing"
    context: str = "general"
    language: Literal["auto", "ar", "en"] = "auto"


class AssistResponse(BaseModel):
    mode: str
    context: str
    output: str
    model: str
    source: str


def _resolve_language(request: AssistRequest) -> Literal["ar", "en"]:
    text = request.text.strip()
    if request.language in {"ar", "en"}:
        return request.language
    if ARABIC_RE.search(text):
        return "ar"
    if LATIN_RE.search(text):
        return "en"
    return "ar"


def _build_assistant_prompt(request: AssistRequest, language: Literal["ar", "en"]) -> str:
    text = request.text.strip() or (
        "\u0627\u0643\u062a\u0628 \u0627\u0642\u062a\u0631\u0627\u062d\u0627\u062a \u0642\u0635\u064a\u0631\u0629 \u0645\u0646\u0627\u0633\u0628\u0629." if language == "ar"
        else "Write short useful suggestions."
    )

    prompts = {
        ("deaf_to_hearing", "ar"): (
            "\u0623\u0646\u062a \u0645\u0633\u0627\u0639\u062f \u0643\u062a\u0627\u0628\u0629 \u0644\u0644\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0623\u0634\u062e\u0627\u0635 \u0627\u0644\u0633\u0627\u0645\u0639\u064a\u0646.\n"
            "\u0627\u0644\u0645\u0647\u0645\u0629: \u062d\u0648\u0644 \u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0642\u0635\u064a\u0631\u0629 \u0623\u0648 \u063a\u064a\u0631 \u0627\u0644\u0645\u0631\u062a\u0628\u0629 \u0625\u0644\u0649 \u062c\u0645\u0644\u0629 \u0639\u0631\u0628\u064a\u0629 \u0648\u0627\u0636\u062d\u0629 \u0648\u0637\u0628\u064a\u0639\u064a\u0629.\n"
            "\u0627\u0644\u0642\u0648\u0627\u0639\u062f: \u0627\u0643\u062a\u0628 \u0628\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0641\u0642\u0637. \u062d\u0627\u0641\u0638 \u0639\u0644\u0649 \u0627\u0644\u0645\u0639\u0646\u0649 \u0648\u0627\u0644\u0641\u0627\u0639\u0644 \u0648\u0627\u0644\u0627\u062a\u062c\u0627\u0647 \u0643\u0645\u0627 \u0647\u064a. \u0644\u0627 \u062a\u0636\u0641 \u062a\u0634\u062e\u064a\u0635\u0627\u064b \u0623\u0648 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u062c\u062f\u064a\u062f\u0629. \u0644\u0627 \u062a\u0639\u0643\u0633 \u0627\u0644\u0645\u0639\u0646\u0649. \u0644\u0627 \u062a\u062a\u062d\u062f\u062b \u0645\u0639 \u0627\u0644\u0645\u0631\u064a\u0636\u060c \u0641\u0642\u0637 \u0623\u0639\u062f \u0635\u064a\u0627\u063a\u0629 \u0643\u0644\u0627\u0645\u0647.\n\n"
            "\u0645\u062b\u0627\u0644 \u062c\u064a\u062f:\n"
            "\u0627\u0644\u0625\u062f\u062e\u0627\u0644: \u062f\u0643\u062a\u0648\u0631 \u0627\u0646\u0627 \u0645\u0627 \u0641\u0647\u0645 \u0643\u0644\u0627\u0645 \u062f\u0648\u0627\u0621\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629: \u062f\u0643\u062a\u0648\u0631\u060c \u0644\u0645 \u0623\u0641\u0647\u0645 \u062a\u0639\u0644\u064a\u0645\u0627\u062a \u0627\u0644\u062f\u0648\u0627\u0621. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0627\u0634\u0631\u062d\u0647\u0627 \u0644\u064a \u0628\u0637\u0631\u064a\u0642\u0629 \u0623\u0628\u0633\u0637.\n\n"
            "\u0645\u062b\u0627\u0644 \u0633\u064a\u0626 (\u0645\u0639\u0646\u0649 \u0645\u0639\u0643\u0648\u0633):\n"
            "\u0627\u0644\u0625\u062f\u062e\u0627\u0644: \u062f\u0643\u062a\u0648\u0631 \u0627\u0646\u0627 \u0645\u0627 \u0641\u0647\u0645 \u0643\u0644\u0627\u0645 \u062f\u0648\u0627\u0621\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0627\u0644\u062e\u0627\u0637\u0626\u0629: \u0627\u0644\u0637\u0628\u064a\u0628 \u0644\u0645 \u064a\u0641\u0647\u0645\u0646\u064a. \u2190 \u062e\u0627\u0637\u0626\u060c \u0627\u0644\u0645\u0639\u0646\u0649 \u0627\u0646\u0639\u0643\u0633.\n\n"
            "\u0645\u062b\u0627\u0644 \u0633\u064a\u0626 (\u0627\u0644\u062a\u062d\u062f\u062b \u0645\u0639 \u0627\u0644\u0645\u0631\u064a\u0636 \u0628\u062f\u0644 \u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0635\u064a\u0627\u063a\u0629):\n"
            "\u0627\u0644\u0625\u062f\u062e\u0627\u0644: \u0631\u0627\u0633\u064a \u064a\u062f\u0648\u0631\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0627\u0644\u062e\u0627\u0637\u0626\u0629: \u0643\u064a\u0641 \u064a\u0645\u0643\u0646\u0646\u064a \u0645\u0633\u0627\u0639\u062f\u062a\u0643\u061f \u2190 \u062e\u0627\u0637\u0626\u060c \u0623\u0646\u062a \u0644\u0627 \u062a\u062a\u062d\u062f\u062b \u0645\u0639 \u0627\u0644\u0645\u0631\u064a\u0636\u060c \u0623\u0646\u062a \u062a\u0639\u064a\u062f \u0635\u064a\u0627\u063a\u0629 \u0643\u0644\u0627\u0645\u0647.\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0627\u0644\u0635\u062d\u064a\u062d\u0629: \u0623\u0634\u0639\u0631 \u0628\u062f\u0648\u0627\u0631 \u0634\u062f\u064a\u062f \u0648\u0644\u0627 \u0623\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0648\u0642\u0648\u0641.\n\n"
            f"\u0627\u0644\u0625\u062f\u062e\u0627\u0644: {text}\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629:"
        ),

        ("deaf_to_hearing", "en"): (
            "You are a communication writing assistant for hearing readers.\n"
            "Task: rewrite the user's rough or short message as one clear, natural English sentence.\n"
            "Rules: write English only. Preserve the exact meaning, speaker, and direction. Do not add diagnosis or new facts. Do not reverse the meaning. Do not answer the user; only rewrite the user's message.\n\n"
            "Good example:\n"
            "Input: I no understand medicine words doctor\n"
            "Answer: Doctor, I did not understand the medicine instructions. Please explain them more simply.\n\n"
            "Bad reversed meaning example:\n"
            "Input: I no understand medicine words doctor\n"
            "Bad answer: The doctor did not understand me. <- wrong, meaning is reversed.\n\n"
            "Bad assistant-role example:\n"
            "Input: my head spinning\n"
            "Bad answer: How can I help you? <- wrong, do not talk to the user, only rewrite their message.\n"
            "Good answer: I feel very dizzy and cannot stand up.\n\n"
            f"Input: {text}\n"
            "Answer:"
        ),

        ("hearing_to_deaf", "ar"): (
            "\u0623\u0646\u062a \u0645\u0633\u0627\u0639\u062f \u0643\u062a\u0627\u0628\u0629 \u0644\u0644\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0634\u062e\u0635 \u0623\u0635\u0645 \u0623\u0648 \u0636\u0639\u064a\u0641 \u0627\u0644\u0633\u0645\u0639.\n"
            "\u0627\u0644\u0645\u0647\u0645\u0629: \u0628\u0633\u0651\u0637 \u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u0625\u0644\u0649 \u0639\u0631\u0628\u064a\u0629 \u0642\u0635\u064a\u0631\u0629 \u0648\u0645\u0628\u0627\u0634\u0631\u0629 \u0648\u0645\u062d\u062a\u0631\u0645\u0629.\n"
            "\u0627\u0644\u0642\u0648\u0627\u0639\u062f: \u0627\u0643\u062a\u0628 \u0628\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0641\u0642\u0637. \u062d\u0627\u0641\u0638 \u0639\u0644\u0649 \u0627\u0644\u0645\u0639\u0646\u0649 \u0648\u0627\u0644\u0641\u0627\u0639\u0644 \u0648\u0627\u0644\u0627\u062a\u062c\u0627\u0647 \u0643\u0645\u0627 \u0647\u064a. \u0644\u0627 \u062a\u0636\u0641 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u062c\u062f\u064a\u062f\u0629.\n\n"
            "\u0645\u062b\u0627\u0644:\n"
            "\u0627\u0644\u0625\u062f\u062e\u0627\u0644: \u064a\u062c\u0628 \u0623\u0646 \u062a\u062a\u0646\u0627\u0648\u0644 \u0627\u0644\u062f\u0648\u0627\u0621 \u0628\u0639\u062f \u0627\u0644\u0623\u0643\u0644 \u0645\u0631\u062a\u064a\u0646 \u064a\u0648\u0645\u064a\u0627\u064b \u0648\u0625\u0630\u0627 \u0627\u0633\u062a\u0645\u0631 \u0627\u0644\u0623\u0644\u0645 \u0631\u0627\u062c\u0639 \u0627\u0644\u0637\u0628\u064a\u0628\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629: \u062e\u0630 \u0627\u0644\u062f\u0648\u0627\u0621 \u0628\u0639\u062f \u0627\u0644\u0623\u0643\u0644 \u0645\u0631\u062a\u064a\u0646 \u0641\u064a \u0627\u0644\u064a\u0648\u0645. \u0625\u0630\u0627 \u0628\u0642\u064a \u0627\u0644\u0623\u0644\u0645\u060c \u0631\u0627\u062c\u0639 \u0627\u0644\u0637\u0628\u064a\u0628.\n\n"
            f"\u0627\u0644\u0625\u062f\u062e\u0627\u0644: {text}\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629:"
        ),

        ("hearing_to_deaf", "en"): (
            "You are a communication assistant for deaf or hard-of-hearing readers.\n"
            "Task: simplify the user's message into short, direct, respectful English.\n"
            "Rules: write English only. Preserve the exact meaning, speaker, and direction. Do not add new facts.\n\n"
            "Example:\n"
            "Input: The patient should take the medicine after food twice daily and should return if the pain continues.\n"
            "Answer: Take the medicine after food two times a day. If the pain continues, see the doctor.\n\n"
            f"Input: {text}\n"
            "Answer:"
        ),

        ("suggestions", "ar"): (
            "\u0623\u0646\u062a \u062a\u0643\u062a\u0628 \u0631\u0633\u0627\u0626\u0644 \u062c\u0627\u0647\u0632\u0629 \u0644\u0644\u0625\u0631\u0633\u0627\u0644 \u0645\u0646 \u0642\u0650\u0628\u064e\u0644 \u0627\u0644\u0645\u0631\u064a\u0636 \u0627\u0644\u0623\u0635\u0645 \u0625\u0644\u0649 \u0637\u0627\u0642\u0645 \u0627\u0644\u0645\u0633\u062a\u0634\u0641\u0649 \u0623\u0648 \u0627\u0644\u0637\u0628\u064a\u0628.\n"
            "\u0627\u0644\u0645\u0647\u0645\u0629: \u0623\u0639\u0637 3 \u0625\u0644\u0649 5 \u0627\u0642\u062a\u0631\u0627\u062d\u0627\u062a \u0639\u0631\u0628\u064a\u0629 \u0642\u0635\u064a\u0631\u0629 \u0648\u0645\u0631\u0642\u0645\u0629 \u062a\u0646\u0627\u0633\u0628 \u0627\u0644\u0646\u0635.\n"
            "\u0627\u0644\u0642\u0648\u0627\u0639\u062f: \u0627\u0643\u062a\u0628 \u0628\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0641\u0642\u0637. \u0644\u0627 \u062a\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629 \u0623\u0648 \u0627\u0644\u0635\u064a\u0646\u064a\u0629. \u0643\u0644 \u0627\u0642\u062a\u0631\u0627\u062d \u064a\u062c\u0628 \u0623\u0646 \u064a\u0643\u0648\u0646 \u062c\u0645\u0644\u0629 \u064a\u0631\u0633\u0644\u0647\u0627 \u0627\u0644\u0645\u0631\u064a\u0636\u060c \u0648\u0644\u064a\u0633 \u0631\u062f\u0627\u064b \u0645\u0646 \u0627\u0644\u0637\u0627\u0642\u0645.\n\n"
            "\u0645\u062b\u0627\u0644 \u062e\u0627\u0637\u0626 (\u0643\u0644\u0627\u0645 \u0627\u0644\u0637\u0627\u0642\u0645\u060c \u0644\u064a\u0633 \u0627\u0644\u0645\u0631\u064a\u0636):\n"
            "\u0643\u064a\u0641 \u064a\u0645\u0643\u0646\u0646\u064a \u0645\u0633\u0627\u0639\u062f\u062a\u0643\u061f \u2190 \u062e\u0627\u0637\u0626.\n"
            "\u0647\u0644 \u062a\u062d\u062a\u0627\u062c \u0625\u0644\u0649 \u0645\u0633\u0627\u0639\u062f\u0629\u061f \u2190 \u062e\u0627\u0637\u0626.\n\n"
            "\u0645\u062b\u0627\u0644 \u0635\u062d\u064a\u062d (\u0643\u0644\u0627\u0645 \u0627\u0644\u0645\u0631\u064a\u0636):\n"
            "1. \u0645\u062a\u0649 \u0645\u0648\u0639\u062f\u064a\u061f\n"
            "2. \u0623\u064a\u0646 \u0623\u0646\u062a\u0638\u0631\u061f\n"
            "3. \u0623\u062d\u062a\u0627\u062c \u0645\u0633\u0627\u0639\u062f\u0629.\n\n"
            "\u0645\u062b\u0627\u0644 \u0643\u0627\u0645\u0644:\n"
            "\u0627\u0644\u0625\u062f\u062e\u0627\u0644: \u0627\u0646\u0627 \u0641\u064a \u0627\u0644\u0645\u0633\u062a\u0634\u0641\u0649 \u0648\u0627\u0631\u064a\u062f \u0627\u0633\u0627\u0644 \u0639\u0646 \u0645\u0648\u0639\u062f\u064a\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629:\n"
            "1. \u0645\u062a\u0649 \u0645\u0648\u0639\u062f\u064a\u061f\n"
            "2. \u0623\u064a\u0646 \u0623\u0646\u062a\u0638\u0631\u061f\n"
            "3. \u0647\u0644 \u062a\u0623\u062e\u0631 \u0645\u0648\u0639\u062f\u064a\u061f\n"
            "4. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0623\u062e\u0628\u0631\u0646\u064a \u0639\u0646\u062f\u0645\u0627 \u064a\u062d\u064a\u0646 \u062f\u0648\u0631\u064a.\n\n"
            f"\u0627\u0644\u0625\u062f\u062e\u0627\u0644: {text}\n"
            "\u0627\u0644\u0625\u062c\u0627\u0628\u0629:"
        ),

        ("suggestions", "en"): (
            "You write ready-to-send messages from the patient to hospital staff or the doctor.\n"
            "Task: give 3 to 5 short numbered English suggestions that fit the context below.\n"
            "Rules: write English only. Each suggestion must be a message the patient sends, not a staff reply.\n\n"
            "Bad examples (staff voice, not patient):\n"
            "How can I help you? <- wrong.\n"
            "Do you need assistance? <- wrong.\n\n"
            "Good examples (patient voice):\n"
            "1. When is my appointment?\n"
            "2. Where should I wait?\n"
            "3. I need help please.\n\n"
            "Full example:\n"
            "Input: I am at the hospital and want to ask about my appointment\n"
            "Answer:\n"
            "1. When is my appointment?\n"
            "2. Where should I wait?\n"
            "3. Has my appointment been delayed?\n"
            "4. Please tell me when it is my turn.\n\n"
            f"Input: {text}\n"
            "Answer:"
        ),
    }

    return prompts[(request.mode, language)]


def _deterministic_fallback(request: AssistRequest, language: Literal["ar", "en"]) -> str:
    text = request.text.strip()

    if request.mode in {"deaf_to_hearing", "hearing_to_deaf"}:
        if text:
            return text
        return (
            "\u0627\u0643\u062a\u0628 \u0627\u0644\u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u062a\u064a \u062a\u0631\u064a\u062f \u0625\u0631\u0633\u0627\u0644\u0647\u0627."
            if language == "ar"
            else "Write the message you want to send."
        )

    # suggestions
    lowered = text.lower()

    if language == "ar":
        if "\u0645\u0648\u0639\u062f" in text:
            return "\n".join([
                "1. \u0645\u062a\u0649 \u0645\u0648\u0639\u062f\u064a\u061f",
                "2. \u0623\u064a\u0646 \u0623\u0646\u062a\u0638\u0631\u061f",
                "3. \u0647\u0644 \u062a\u0623\u062e\u0631 \u0645\u0648\u0639\u062f\u064a\u061f",
                "4. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0623\u062e\u0628\u0631\u0646\u064a \u0639\u0646\u062f\u0645\u0627 \u064a\u062d\u064a\u0646 \u062f\u0648\u0631\u064a.",
            ])
        if "\u062f\u0648\u0627\u0621" in text or "\u0639\u0644\u0627\u062c" in text or "\u062d\u0628\u0629" in text:
            return "\n".join([
                "1. \u0645\u062a\u0649 \u0622\u062e\u0630 \u0627\u0644\u062f\u0648\u0627\u0621\u061f",
                "2. \u0643\u0645 \u0645\u0631\u0629 \u0641\u064a \u0627\u0644\u064a\u0648\u0645\u061f",
                "3. \u0647\u0644 \u0622\u062e\u0630\u0647 \u0642\u0628\u0644 \u0627\u0644\u0623\u0643\u0644 \u0623\u0645 \u0628\u0639\u062f\u0647\u061f",
                "4. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0627\u0643\u062a\u0628 \u062a\u0639\u0644\u064a\u0645\u0627\u062a \u0627\u0644\u062f\u0648\u0627\u0621.",
            ])
        if "\u0623\u0644\u0645" in text or "\u0648\u062c\u0639" in text or "\u0627\u0644\u0645" in text:
            return "\n".join([
                "1. \u0623\u0634\u0639\u0631 \u0628\u0623\u0644\u0645.",
                "2. \u0627\u0644\u0623\u0644\u0645 \u0642\u0648\u064a.",
                "3. \u0623\u062d\u062a\u0627\u062c \u0645\u0633\u0627\u0639\u062f\u0629 \u0645\u0646 \u0641\u0636\u0644\u0643.",
                "4. \u0647\u0644 \u064a\u0645\u0643\u0646\u0643 \u0623\u0646 \u062a\u0634\u0631\u062d \u0644\u064a \u0645\u0627\u0630\u0627 \u0623\u0641\u0639\u0644\u061f",
            ])
        return "\n".join([
            "1. \u0623\u062d\u062a\u0627\u062c \u0645\u0633\u0627\u0639\u062f\u0629.",
            "2. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0627\u0634\u0631\u062d \u0628\u0637\u0631\u064a\u0642\u0629 \u0623\u0628\u0633\u0637.",
            "3. \u0647\u0644 \u064a\u0645\u0643\u0646\u0643 \u0627\u0644\u0643\u062a\u0627\u0628\u0629\u061f",
            "4. \u0623\u062d\u062a\u0627\u062c \u062f\u0642\u064a\u0642\u0629 \u0645\u0646 \u0641\u0636\u0644\u0643.",
        ])

    # English suggestions fallback
    if "appointment" in lowered:
        return "\n".join([
            "1. When is my appointment?",
            "2. Where should I wait?",
            "3. Has my appointment been delayed?",
            "4. Please tell me when it is my turn.",
        ])
    if "medicine" in lowered or "medication" in lowered or "pill" in lowered:
        return "\n".join([
            "1. When should I take the medicine?",
            "2. How many times a day?",
            "3. Before or after food?",
            "4. Please write the medicine instructions.",
        ])
    if "pain" in lowered or "hurt" in lowered:
        return "\n".join([
            "1. I am in pain.",
            "2. The pain is strong.",
            "3. I need help please.",
            "4. Can you explain what I should do?",
        ])
    return "\n".join([
        "1. I need help.",
        "2. Please explain more simply.",
        "3. Can you write that down?",
        "4. I need a moment please.",
    ])


def _output_is_wrong_script(output: str, language: Literal["ar", "en"]) -> bool:
    if CJK_RE.search(output):
        return True
    if language == "ar":
        arabic_count = len(ARABIC_RE.findall(output))
        latin_count = len(LATIN_RE.findall(output))
        return arabic_count == 0 or latin_count > arabic_count
    return False


def _clean_assistant_output(
    output: str,
    request: AssistRequest,
    language: Literal["ar", "en"],
) -> str:
    cleaned = output.replace("\r\n", "\n").replace("\r", "\n").strip()

    hard_cut_markers = [
        "←",
        "\nالإجابة:",
        "\nAnswer:",
        "\nInput:",
        "\nالإدخال:",
        "\nمثال",
        "\nBad ",
        "\nGood ",
        "\nRules:",
        "\nTask:",
        "\nالقواعد:",
        "\nالمهمة:",
        "\nمثال",
    ]
    inline_cut_markers = [
        " يجب إعادة",
        " لا تتحدث",
        " حافظ على",
        " المعنى صحيح",
        " المعنى واضح",
        " الإجابة:",
        " كيف يمكنني مساعدتك؟",
        " هل يمكنك كتابة الرسالة؟",
        " لكن يمكنني مساعدتك",
    ]

    for marker in hard_cut_markers + inline_cut_markers:
        index = cleaned.find(marker)
        if index > 0:
            cleaned = cleaned[:index].strip()

    cleaned = cleaned.replace("دواعش شديدة", "دوار شديد").replace("دواعش", "دوار")

    if request.mode == "suggestions":
        cleaned = _clean_suggestions_output(cleaned, language)
    else:
        cleaned = cleaned.splitlines()[0].strip() if cleaned.splitlines() else cleaned

    cleaned = cleaned.strip(" \n\t:-")
    return cleaned


def _clean_suggestions_output(output: str, language: Literal["ar", "en"]) -> str:
    blocked = (
        "كيف يمكنني مساعدتك",
        "هل تحتاج",
        "do you need",
        "how can i help",
    )
    lines = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.lower() in line.lower() for pattern in blocked):
            continue
        lines.append(line)

    if not lines:
        return ""

    numbered = []
    for index, line in enumerate(lines[:5], start=1):
        line = re.sub(r"^\s*\d+\s*[\.\)-]\s*", "", line).strip()
        if line:
            numbered.append(f"{index}. {line}")
    return "\n".join(numbered)


@app.post("/ai/assist", response_model=AssistResponse)
def assist_message(request: AssistRequest):
    language = _resolve_language(request)
    prompt = _build_assistant_prompt(request, language)

    try:
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/generate",
            json={
                "model": ASSISTANT_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.6,
                    "num_predict": 140 if request.mode == "suggestions" else 80,
                    "stop": [
                        "\n\n\n",
                        "←",
                        "Input:",
                        "Answer:",
                        "Bad ",
                        "Good ",
                        "Rules:",
                        "Task:",
                        "\u0627\u0644\u0625\u062f\u062e\u0627\u0644:",
                        "\u0627\u0644\u0625\u062c\u0627\u0628\u0629:",
                        "\u0645\u062b\u0627\u0644",
                        "\u0627\u0644\u0642\u0648\u0627\u0639\u062f:",
                        "\u0627\u0644\u0645\u0647\u0645\u0629:",
                    ],
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        output = str(response.json().get("response", "")).strip()

        if not output:
            raise ValueError("Empty response from assistant model")

        source = "ollama"
        cleaned_output = _clean_assistant_output(output, request, language)
        if cleaned_output and cleaned_output != output:
            output = cleaned_output
            source = "ollama_cleaned"
        elif not cleaned_output:
            output = _deterministic_fallback(request, language)
            source = "fallback"

        if _output_is_wrong_script(output, language):
            print(f"[AI assist] Wrong script for lang={language}, falling back. Output was: {output[:80]!r}")
            output = _deterministic_fallback(request, language)
            source = "fallback"

        return AssistResponse(
            mode=request.mode,
            context=request.context,
            output=output,
            model=ASSISTANT_MODEL,
            source=source,
        )

    except Exception as exc:
        print(f"[AI assist] Exception: {exc}")
        return AssistResponse(
            mode=request.mode,
            context=request.context,
            output=_deterministic_fallback(request, language),
            model=ASSISTANT_MODEL,
            source="fallback",
        )
