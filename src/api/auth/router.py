from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.api.database.connection import get_db
from src.api.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserUpdateRequest,
    ChangePasswordRequest,
    MessageResponse,
    UserResponse,
    TokenResponse,
    PredictionHistoryListResponse,
    PredictionHistoryResponse,
)
from src.api.auth.security import hash_password, verify_password, create_access_token
from src.api.auth.dependencies import get_current_user
from src.api.models.user import User
from src.api.models.prediction_history import PredictionHistory

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.email == req.email, User.username == req.username)
    ).first()
    if existing:
        if existing.email == req.email:
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for the authenticated user (requires current password)."""
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return MessageResponse(message="Password updated successfully")


@router.put("/me", response_model=UserResponse)
def update_profile(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.username is not None:
        conflict = db.query(User).filter(
            User.username == req.username, User.id != current_user.id
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Username already taken")
        current_user.username = req.username

    if req.email is not None:
        conflict = db.query(User).filter(
            User.email == req.email, User.id != current_user.id
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Email already registered")
        current_user.email = req.email

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/history", response_model=PredictionHistoryListResponse)
def get_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PredictionHistory).filter(
        PredictionHistory.user_id == current_user.id
    ).order_by(PredictionHistory.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PredictionHistoryListResponse(
        items=[PredictionHistoryResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
