from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
    normalise_mobile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower()
    existing = db.scalar(
        select(User).where((User.email == email) | (User.mobile == payload.mobile))
    )
    if existing is not None:
        field = "email address" if existing.email == email else "mobile number"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with this {field} already exists",
        )

    user = User(
        full_name=payload.full_name,
        email=email,
        mobile=payload.mobile,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    identifier = payload.identifier.strip()
    mobile = normalise_mobile(identifier)
    user = db.scalar(
        select(User).where(
            (User.email == identifier.lower()) | (User.mobile == mobile)
            if mobile
            else (User.email == identifier.lower())
        )
    )

    # Same generic message for unknown account and wrong password.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile or password",
        )
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(_: User = Depends(get_current_user)) -> dict[str, str]:
    """Stateless JWT: the client discards the token. No server-side session to clear."""
    return {"detail": "Logged out. Discard the access token on the client."}
