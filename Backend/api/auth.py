import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, session
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, func
from pydantic import validator
from itsdangerous import URLSafeTimedSerializer
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import random

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

# Initialize URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

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
    province: Optional[str] = None
    postal_code: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    user_type: UserType
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

    @validator('user_type', pre=True)
    def convert_user_type_to_upper(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

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
        user_type = payload.get("user_type")
        
        # Log token contents for debugging
        logger.info(f"Token payload: email={email}, user_id={user_id}, user_type={user_type}")
        
        if email is None or user_id is None or user_type is None:
            logger.error("Missing required claims in token")
            raise credentials_exception
            
        token_data = TokenData(email=email, user_id=user_id, user_type=user_type)
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception

    # Debug the query we're using to find the user
    query = select(User).where(
        and_(
            User.id == token_data.user_id,
            User.email == token_data.email,
            func.upper(User.user_type) == token_data.user_type
        )
    )
    logger.info(f"User lookup query: {query}")
    
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.error(f"User not found for token data: {token_data}")
        # Try a simpler query to debug why we can't find the user
        simple_query = select(User).where(User.id == token_data.user_id)
        simple_result = await session.execute(simple_query)
        simple_user = simple_result.scalar_one_or_none()
        
        if simple_user:
            logger.info(f"Found user by ID only: {simple_user.id}, email={simple_user.email}, type={simple_user.user_type}")
            logger.info(f"User type comparison: token={token_data.user_type}, db={simple_user.user_type}")
            
            # If only the case is different, update the user type to match the token
            if simple_user.user_type.upper() == token_data.user_type.upper():
                logger.info(f"Updating user type from {simple_user.user_type} to {token_data.user_type}")
                simple_user.user_type = token_data.user_type
                await session.commit()
                return simple_user
        
        raise credentials_exception
        
    logger.info(f"User authenticated: id={user.id}, email={user.email}, type={user.user_type}")
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

    # Convert user_type to uppercase to match the enum
    user_type = user.user_type.upper()
    
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "user_type": user_type}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user_type
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
        province=user_data.province,
        postal_code=user_data.postal_code,
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# === Email Verification ===
async def send_verification_email(user: User):
    token = serializer.dumps(user.email, salt='email-confirm')
    verification_link = f"http://yourdomain.com/auth/verify-email?token={token}"
    message = Mail(
        from_email='no-reply@yourdomain.com',
        to_emails=user.email,
        subject='Verify your email',
        html_content=f'<p>Please verify your email by clicking <a href="{verification_link}">here</a>.</p>'
    )
    try:
        # TODO: Replace with actual SendGrid API key
        sg = SendGridAPIClient('SENDGRID_API_KEY')
        response = sg.send(message)
        logger.info(f"Email sent to {user.email}: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_email_verified = True
    await session.commit()
    return {"message": "Email verified successfully"}

# === Email Verification ===
@router.post("/resend-verification")
async def resend_verification(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not current_user.is_email_verified:
        await send_verification_email(current_user)
    return {"message": "Verification email resent successfully"}
