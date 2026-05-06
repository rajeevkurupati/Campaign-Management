"""
Auth endpoints: register, login, me.
All paths are prefixed with /auth in main.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth.models import LoginRequest, Token, User, UserCreate, UserRead
from auth.utils import create_access_token, hash_password, verify_password
from auth.dependencies import get_current_user
from database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
def register(payload: UserCreate, session: Session = Depends(get_session)):
    """Create a new user account and return a JWT token."""
    existing = session.exec(select(User).where(User.email == payload.email.lower().strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = User(
        email=payload.email.lower().strip(),
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        plan=payload.plan,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    """Authenticate with email + password and return a JWT token."""
    user = session.exec(
        select(User).where(User.email == payload.email.lower().strip())
    ).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserRead.model_validate(current_user)
