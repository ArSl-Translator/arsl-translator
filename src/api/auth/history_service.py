from typing import Optional, Dict

from sqlalchemy.orm import Session

from src.api.models.prediction_history import PredictionHistory
from src.api.models.user import User


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
        prediction_type=prediction_type[:64],
        top_prediction_label=str(top.get("label_id", "")),
        top_prediction_text=top.get("text", ""),
        top_prediction_confidence=top.get("confidence"),
        all_predictions=result.get("top_k_predictions"),
    )
    db.add(record)
    db.commit()
