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
        "assistant": {
            "model": ASSISTANT_MODEL,
            "url": OLLAMA_URL,
        },
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


AssistantMode = Literal[
    "deaf_to_hearing",
    "hearing_to_deaf",
    "suggestions",
]


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
    text = request.text.strip() or ("اكتب اقتراحات قصيرة مناسبة." if language == "ar" else "Write short useful suggestions.")

    prompts = {
        ("deaf_to_hearing", "ar"): f"""أنت مساعد كتابة للتواصل مع الأشخاص السامعين.
المهمة: حوّل رسالة المستخدم القصيرة أو غير المرتبة إلى جملة عربية واضحة وطبيعية.
القواعد: اكتب بالعربية فقط. حافظ على المعنى والفاعل والاتجاه كما هي. لا تضف تشخيصا أو معلومات جديدة. لا تعكس المعنى.
مثال جيد:
الإدخال: دكتور انا ما فهم كلام دواء
الإجابة: دكتور، لم أفهم تعليمات الدواء. من فضلك اشرحها لي بطريقة أبسط.
مثال سيئ لمعنى معكوس: الطبيب لم يفهمني.
الإدخال: {text}
الإجابة:""",
        ("deaf_to_hearing", "en"): f"""You are a communication writing assistant for hearing readers.
Task: rewrite the user's rough or short message as one clear, natural English sentence.
Rules: write English only. Preserve the exact meaning, speaker, and direction. Do not add diagnosis or new facts. Do not reverse the meaning.
Good example:
Input: I no understand medicine words doctor
Answer: Doctor, I did not understand the medicine instructions. Please explain them more simply.
Bad reversed meaning: The doctor did not understand me.
Input: {text}
Answer:""",
        ("hearing_to_deaf", "ar"): f"""أنت مساعد كتابة للتواصل مع شخص أصم أو ضعيف السمع.
المهمة: بسّط رسالة المستخدم إلى عربية قصيرة ومباشرة ومحترمة.
القواعد: اكتب بالعربية فقط. حافظ على المعنى والفاعل والاتجاه كما هي. لا تضف معلومات جديدة.
مثال:
الإدخال: يجب أن تتناول الدواء بعد الأكل مرتين يوميا وإذا استمر الألم راجع الطبيب
الإجابة: خذ الدواء بعد الأكل مرتين في اليوم. إذا بقي الألم، راجع الطبيب.
الإدخال: {text}
الإجابة:""",
        ("hearing_to_deaf", "en"): f"""You are a communication assistant for deaf or hard-of-hearing readers.
Task: simplify the user's message into short, direct, respectful English.
Rules: write English only. Preserve the exact meaning, speaker, and direction. Do not add new facts.
Example:
Input: The patient should take the medicine after food twice daily and should return if the pain continues.
Answer: Take the medicine after food two times a day. If the pain continues, see the doctor.
Input: {text}
Answer:""",
        ("suggestions", "ar"): f"""أنت مساعد يكتب عبارات جاهزة للإرسال في محادثة طبية أو يومية.
المهمة: أعط 3 إلى 5 اقتراحات عربية قصيرة ومرقمة تناسب النص.
القواعد: اكتب بالعربية فقط. لا تستخدم الصينية أو الإنجليزية. اجعل كل اقتراح جاهزا للإرسال.
مثال:
الإدخال: انا في المستشفى واريد اسأل عن موعدي
الإجابة:
1. متى موعدي؟
2. أين أنتظر؟
3. هل تأخر موعدي؟
الإدخال: {text}
الإجابة:""",
        ("suggestions", "en"): f"""You write ready-to-send chat phrases for medical or everyday communication.
Task: give 3 to 5 short numbered English suggestions that fit the text.
Rules: write English only. Each suggestion must be ready to send.
Example:
Input: I am at the hospital and want to ask about my appointment
Answer:
1. When is my appointment?
2. Where should I wait?
3. Has my appointment been delayed?
Input: {text}
Answer:""",
    }
    return prompts[(request.mode, language)]


def _deterministic_fallback(request: AssistRequest, language: Literal["ar", "en"]) -> str:
    text = request.text.strip()
    if request.mode in {"deaf_to_hearing", "hearing_to_deaf"}:
        if text:
            return text
        return "اكتب الرسالة التي تريد إرسالها." if language == "ar" else "Write the message you want to send."

    lowered = text.lower()
    if language == "ar":
        if "موعد" in text:
            return "\n".join(["1. متى موعدي؟", "2. أين أنتظر؟", "3. هل تأخر موعدي؟", "4. من فضلك أخبرني عندما يحين دوري."])
        if "دواء" in text or "علاج" in text:
            return "\n".join(["1. متى آخذ الدواء؟", "2. كم مرة آخذ الدواء؟", "3. هل آخذه قبل الأكل أو بعده؟", "4. من فضلك اكتب تعليمات الدواء."])
        if "ألم" in text or "الم" in text or "وجع" in text:
            return "\n".join(["1. أشعر بألم.", "2. الألم قوي.", "3. أحتاج مساعدة من فضلك.", "4. هل يمكن أن تشرح لي ماذا أفعل؟"])
        return "\n".join(["1. أحتاج مساعدة.", "2. من فضلك اشرح بطريقة أبسط.", "3. هل يمكنك كتابة الكلام؟", "4. أحتاج دقيقة من فضلك."])

    if "appointment" in lowered:
        return "\n".join(["1. When is my appointment?", "2. Where should I wait?", "3. Has my appointment been delayed?", "4. Please tell me when it is my turn."])
    if "medicine" in lowered or "medication" in lowered:
        return "\n".join(["1. When should I take the medicine?", "2. How many times should I take it?", "3. Should I take it before or after food?", "4. Please write the medicine instructions."])
    if "pain" in lowered or "hurt" in lowered:
        return "\n".join(["1. I am in pain.", "2. The pain is strong.", "3. I need help, please.", "4. Can you explain what I should do?"])
    return "\n".join(["1. I need help.", "2. Please explain more simply.", "3. Can you write that down?", "4. I need a moment."])


def _output_is_wrong_script(output: str, language: Literal["ar", "en"]) -> bool:
    if CJK_RE.search(output):
        return True

    if language == "ar":
        arabic_count = len(ARABIC_RE.findall(output))
        latin_count = len(LATIN_RE.findall(output))
        return arabic_count == 0 or latin_count > arabic_count

    return False


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
                    "top_p": 1.0,
                    "num_predict": 220,
                    "stop": ["\n\n\n", "Input:", "الإدخال:"],
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        output = str(response.json().get("response", "")).strip()
        if not output:
            raise ValueError("Empty response from assistant model")
        source = "ollama"
        if _output_is_wrong_script(output, language):
            output = _deterministic_fallback(request, language)
            source = "fallback"
        return AssistResponse(
            mode=request.mode,
            context=request.context,
            output=output,
            model=ASSISTANT_MODEL,
            source=source,
        )
    except Exception:
        return AssistResponse(
            mode=request.mode,
            context=request.context,
            output=_deterministic_fallback(request, language),
            model=ASSISTANT_MODEL,
            source="fallback",
        )
