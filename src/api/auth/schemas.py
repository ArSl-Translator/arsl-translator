from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[str] = Field(None, min_length=5, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PredictionHistoryResponse(BaseModel):
    id: int
    prediction_type: str
    top_prediction_label: Optional[str] = None
    top_prediction_text: Optional[str] = None
    top_prediction_confidence: Optional[float] = None
    all_predictions: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionHistoryListResponse(BaseModel):
    items: List[PredictionHistoryResponse]
    total: int
    page: int
    page_size: int
