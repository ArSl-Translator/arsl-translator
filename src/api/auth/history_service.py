from typing import Optional, Dict

from sqlalchemy.orm import Session

from src.api.models.prediction_history import PredictionHistory
from src.api.models.user import User


def _compact_prediction_type(prediction_type: str) -> str:
    return (
        prediction_type
        .replace("karsl_mediapipe", "karsl_mp")
        .replace("arab-sign", "arabsign")
        .replace("arab_sign", "arabsign")
    )[:64]


def save_prediction(
    db: Session,
    user: Optional[User],
    prediction_type: str,
    result: Dict,
):
    """Save prediction to history if user is authenticated."""
    if user is None:
        return

    top = result.get("top_prediction") or {}
    record = PredictionHistory(
        user_id=user.id,
        prediction_type=_compact_prediction_type(prediction_type),
        top_prediction_label=str(top.get("label_id", ""))[:20],
        top_prediction_text=str(top.get("text", ""))[:255],
        top_prediction_confidence=top.get("confidence"),
        all_predictions=result.get("top_k_predictions"),
    )
    db.add(record)
    db.commit()
