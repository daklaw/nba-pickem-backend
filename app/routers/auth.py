from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.models import User, Season
from app.schemas.schemas import Token, UserCreate, UserResponse
from datetime import timedelta
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint - authenticate user and return JWT token.
    """
    # Find user by email (username field in OAuth2PasswordRequestForm)
    user = db.query(User).filter(User.email == form_data.username).first()
    print(f"Password: {form_data.password}")
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Get the current (most recent) season for the user's league
    current_season = db.query(Season).filter(
        Season.league_id == user.league_id
    ).order_by(Season.year.desc()).first()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "current_season_id": current_season.id if current_season else None
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint - with JWT, logout is handled client-side by deleting the token.
    This endpoint is here for consistency, but the actual logout logic should be
    implemented on the frontend by removing the stored token.
    """
    return {"message": "Successfully logged out. Please delete your access token."}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        league_id=user_data.league_id,
        total_points=0
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user