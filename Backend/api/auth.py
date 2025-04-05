import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from Backend.config import settings
from Backend.database import get_session
from Backend.models.user import User, UserType

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# Set up password hashing and JWT authentication
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# === Models ===
class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: UserType

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    user_type: Optional[UserType] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    user_type: UserType
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    user_type: UserType
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_admin: bool

# === Password + Token Helpers ===
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# === Authentication ===
async def authenticate_user(email: str, password: str, session: AsyncSession):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception

    result = await session.execute(
        select(User).where(User.id == token_data.user_id, User.email == token_data.email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# === API Routes ===
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    user = await authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "user_type": user.user_type}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user.user_type
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,  # <-- FIXED
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        user_type=user_data.user_type,
        phone=user_data.phone,
        address=user_data.address,
        city=user_data.city,
        state=user_data.state,
        zip_code=user_data.zip_code,
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
