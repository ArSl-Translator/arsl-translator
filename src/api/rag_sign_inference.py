import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from src.api.karsl_mediapipe_inference import HAND_LANDMARKER_MODEL_PATH


DEFAULT_INDEX_DIR = os.getenv("RAG_SIGN_INDEX_DIR", "./models/rag_sign_index")
DEFAULT_COLLECTION = os.getenv("RAG_SIGN_COLLECTION", "arabic_sign_language")
DEFAULT_CLIP_MODEL = os.getenv("RAG_SIGN_CLIP_MODEL", "clip-ViT-L-14")
DEFAULT_FRAMES = int(os.getenv("RAG_SIGN_FRAMES", "10"))
DEFAULT_YOLO_CONF = float(os.getenv("RAG_SIGN_YOLO_CONF", "0.40"))
DEFAULT_PAD = int(os.getenv("RAG_SIGN_PAD", "30"))
DEFAULT_IMG_SIZE = int(os.getenv("RAG_SIGN_IMG_SIZE", "224"))
DEFAULT_USE_REMBG = os.getenv("RAG_SIGN_USE_REMBG", "false").lower() in {
    "1",
    "true",
    "yes",
}


LABEL_TEXT: Dict[str, str] = {
    "ain": "ع",
    "al": "ال",
    "alef": "ا",
    "beh": "ب",
    "dad": "ض",
    "dal": "د",
    "feh": "ف",
    "ghain": "غ",
    "hah": "ح",
    "heh": "ه",
    "jeem": "ج",
    "kaf": "ك",
    "khah": "خ",
    "laa": "لا",
    "lam": "ل",
    "meem": "م",
    "noon": "ن",
    "qaf": "ق",
    "reh": "ر",
    "sad": "ص",
    "seen": "س",
    "sheen": "ش",
    "tah": "ط",
    "teh": "ت",
    "teh_marbuta": "ة",
    "thal": "ذ",
    "theh": "ث",
    "waw": "و",
    "yeh": "ي",
    "zah": "ظ",
    "zain": "ز",
}


def resolve_chroma_index_dir(index_dir: str = DEFAULT_INDEX_DIR) -> Optional[str]:
    """Return the directory that actually contains Chroma's sqlite database."""
    root = Path(index_dir)
    if not root.exists():
        return None
    if (root / "chroma.sqlite3").is_file():
        return str(root)
    matches = sorted(root.rglob("chroma.sqlite3"))
    if not matches:
        return None
    return str(matches[0].parent)


def rag_sign_index_available(index_dir: str = DEFAULT_INDEX_DIR) -> bool:
    return resolve_chroma_index_dir(index_dir) is not None


class ArabicAlphabetRAGInference:
    """CLIP + Chroma retrieval model for the Arabic alphabet sign index."""

    def __init__(
        self,
        index_dir: str = DEFAULT_INDEX_DIR,
        collection_name: str = DEFAULT_COLLECTION,
        clip_model_name: str = DEFAULT_CLIP_MODEL,
        hand_model_path: str = HAND_LANDMARKER_MODEL_PATH,
        frames_to_sample: int = DEFAULT_FRAMES,
        yolo_conf: float = DEFAULT_YOLO_CONF,
        pad: int = DEFAULT_PAD,
        img_size: int = DEFAULT_IMG_SIZE,
        use_rembg: bool = DEFAULT_USE_REMBG,
    ):
        resolved = resolve_chroma_index_dir(index_dir)
        if not resolved:
            raise FileNotFoundError(
                f"RAG sign index not found under {index_dir}. "
                "Unzip sign_index.zip into models/rag_sign_index."
            )

        import chromadb
        from sentence_transformers import SentenceTransformer

        _patch_chroma_int_seq_id()

        self.index_dir = resolved
        self.collection_name = collection_name
        self.clip_model_name = clip_model_name
        self.hand_model_path = hand_model_path
        self.frames_to_sample = frames_to_sample
        self.yolo_conf = yolo_conf
        self.pad = pad
        self.img_size = img_size
        self.use_rembg = use_rembg
        self._hand_landmarker = None
        self._yolo = None
        self._rembg_remove = None

        self.client = chromadb.PersistentClient(path=self.index_dir)
        self.collection = self.client.get_collection(name=self.collection_name)
        self.index_size = int(self.collection.count())
        if self.index_size <= 0:
            raise ValueError(f"RAG sign collection '{self.collection_name}' is empty")

        self.embedder = SentenceTransformer(self.clip_model_name)

    def predict_video(self, video_path: str, top_k: int = 5) -> Dict:
        frames = self._sample_video_frames(video_path)
        return self.predict_frames(frames, top_k=top_k)

    def predict_frames(self, frames: List[np.ndarray], top_k: int = 5) -> Dict:
        if not frames:
            raise ValueError("No frames provided")

        sampled = self._uniform_sample(frames, self.frames_to_sample)
        images = [self._preprocess_frame(frame) for frame in sampled]
        images = [image for image in images if image is not None]
        if not images:
            raise ValueError("No usable hand/image crop found in frames")

        embeddings = self.embedder.encode(
            images,
            batch_size=min(8, len(images)),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        votes: Dict[str, int] = {}
        scores: Dict[str, float] = {}
        best_score: Dict[str, float] = {}
        query_k = max(1, min(top_k, self.index_size))

        for embedding in embeddings:
            result = self.collection.query(
                query_embeddings=[embedding.tolist()],
                n_results=query_k,
                include=["metadatas", "distances"],
            )
            labels = self._labels_from_query(result)
            for rank, (label, similarity) in enumerate(labels):
                # The first neighbor is strongest, but top-k neighbors still vote.
                weight = 1.0 / float(rank + 1)
                votes[label] = votes.get(label, 0) + 1
                scores[label] = scores.get(label, 0.0) + similarity * weight
                best_score[label] = max(best_score.get(label, 0.0), similarity)

        if not votes:
            raise ValueError("No labels returned from the RAG index")

        ranked = sorted(
            votes.keys(),
            key=lambda label: (votes[label], scores[label], best_score[label]),
            reverse=True,
        )[:top_k]

        predictions = [
            {
                "label_id": label,
                "text": self._label_to_text(label),
                "confidence": float(max(0.0, min(1.0, best_score[label]))),
            }
            for label in ranked
        ]

        return {
            "top_prediction": predictions[0] if predictions else None,
            "top_k_predictions": predictions,
            "model": "arsl_rag",
            "frames_used": len(images),
            "index_size": self.index_size,
            "index_dir": self.index_dir,
        }

    def _sample_video_frames(self, video_path: str) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames: List[np.ndarray] = []
        if total > 0:
            indices = self._uniform_indices(total, self.frames_to_sample)
            for index in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                if ok:
                    frames.append(frame)
        else:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frames.append(frame)
            frames = self._uniform_sample(frames, self.frames_to_sample)

        cap.release()
        if not frames:
            raise ValueError(f"No frames found in video: {video_path}")
        return frames

    def _preprocess_frame(self, frame: np.ndarray) -> Optional[Image.Image]:
        crop = self._crop_with_hand_landmarker(frame)
        if crop is None:
            crop = self._crop_with_yolo(frame)
        if crop is None:
            crop = self._center_crop(frame)

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb).resize((self.img_size, self.img_size))

        if self.use_rembg:
            image = self._remove_background(image)

        return image.convert("RGB")

    def _crop_with_hand_landmarker(self, frame: np.ndarray) -> Optional[np.ndarray]:
        landmarker = self._get_hand_landmarker()
        if landmarker is None:
            return None

        import mediapipe as mp

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not result.hand_landmarks:
            return None

        height, width = frame.shape[:2]
        xs: List[int] = []
        ys: List[int] = []
        for hand in result.hand_landmarks:
            for landmark in hand:
                xs.append(int(landmark.x * width))
                ys.append(int(landmark.y * height))

        return self._crop_box(frame, min(xs), min(ys), max(xs), max(ys))

    def _crop_with_yolo(self, frame: np.ndarray) -> Optional[np.ndarray]:
        yolo = self._get_yolo()
        if yolo is None:
            return None

        results = yolo.predict(frame, conf=self.yolo_conf, verbose=False)
        boxes = getattr(results[0], "boxes", None) if results else None
        if boxes is None or len(boxes) == 0:
            return None

        largest: Optional[Tuple[int, int, int, int]] = None
        largest_area = 0.0
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int).tolist()
            area = max(0, x2 - x1) * max(0, y2 - y1)
            if area > largest_area:
                largest = (x1, y1, x2, y2)
                largest_area = area

        if largest is None:
            return None
        return self._crop_box(frame, *largest)

    def _crop_box(self, frame: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Optional[np.ndarray]:
        height, width = frame.shape[:2]
        x1 = max(0, x1 - self.pad)
        y1 = max(0, y1 - self.pad)
        x2 = min(width, x2 + self.pad)
        y2 = min(height, y2 + self.pad)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    def _center_crop(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        side = min(height, width)
        x1 = max(0, (width - side) // 2)
        y1 = max(0, (height - side) // 2)
        return frame[y1 : y1 + side, x1 : x1 + side]

    def _remove_background(self, image: Image.Image) -> Image.Image:
        try:
            if self._rembg_remove is None:
                from rembg import remove

                self._rembg_remove = remove
            removed = self._rembg_remove(image.convert("RGBA"))
            background = Image.new("RGBA", removed.size, (255, 255, 255, 255))
            background.alpha_composite(removed)
            return background.convert("RGB")
        except Exception:
            return image

    def _get_hand_landmarker(self):
        if self._hand_landmarker is not None:
            return self._hand_landmarker
        if not os.path.isfile(self.hand_model_path):
            return None

        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
            VisionTaskRunningMode,
        )

        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=self.hand_model_path),
            running_mode=VisionTaskRunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.35,
            min_hand_presence_confidence=0.35,
            min_tracking_confidence=0.35,
        )
        self._hand_landmarker = mp_vision.HandLandmarker.create_from_options(options)
        return self._hand_landmarker

    def _get_yolo(self):
        if self._yolo is not None:
            return self._yolo
        try:
            from ultralytics import YOLO

            self._yolo = YOLO("yolov8s.pt")
            return self._yolo
        except Exception:
            return None

    @staticmethod
    def _labels_from_query(result: Dict) -> List[Tuple[str, float]]:
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]
        labels: List[Tuple[str, float]] = []
        for metadata, distance in zip(metadatas[0], distances[0]):
            label = str((metadata or {}).get("label", "")).strip()
            if not label:
                continue
            similarity = 1.0 / (1.0 + max(0.0, float(distance)))
            labels.append((label, similarity))
        return labels

    @staticmethod
    def _label_to_text(label: str) -> str:
        key = label.strip().lower().replace("-", "_").replace(" ", "_")
        return LABEL_TEXT.get(key, label)

    @staticmethod
    def _uniform_indices(n: int, target: int) -> List[int]:
        if n <= 0:
            return []
        if n >= target:
            return np.linspace(0, n - 1, target).round().astype(int).tolist()
        indices = list(range(n))
        indices.extend([n - 1] * (target - n))
        return indices

    def _uniform_sample(self, frames: List[np.ndarray], target: int) -> List[np.ndarray]:
        return [frames[index] for index in self._uniform_indices(len(frames), target)]


def _patch_chroma_int_seq_id() -> None:
    """Allow Chroma 0.5 to read older SQLite indexes whose seq_id is stored as int."""
    try:
        from chromadb.segment.impl.metadata import sqlite as chroma_sqlite
    except Exception:
        return

    original = getattr(chroma_sqlite, "_decode_seq_id", None)
    if original is None or getattr(original, "_arsl_accepts_int", False):
        return

    def decode_seq_id(seq_id):
        if isinstance(seq_id, int):
            return seq_id
        return original(seq_id)

    decode_seq_id._arsl_accepts_int = True
    chroma_sqlite._decode_seq_id = decode_seq_id
