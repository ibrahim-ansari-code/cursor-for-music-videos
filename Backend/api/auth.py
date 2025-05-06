import logging
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
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
from Backend.utils.azure_blob import upload_avatar_to_blob

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

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    password: str

class AvatarUploadResponse(BaseModel):
    profile_image_url: str

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
        
        logger.debug(f"Token payload: email={email}, user_id={user_id}, user_type={user_type}")
        
        if email is None or user_id is None or user_type is None:
            logger.error("Missing required claims in token")
            raise credentials_exception
            
        token_data = TokenData(email=email, user_id=user_id, user_type=user_type)
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception

    # Use a simpler query first based on user_id, then validate email/type
    user = await session.get(User, token_data.user_id)
    
    if user is None:
        logger.error(f"User not found for ID in token: {token_data.user_id}")
        raise credentials_exception
        
    # Validate email and user type match the token
    if user.email != token_data.email or user.user_type.upper() != token_data.user_type.upper():
        logger.error(f"Token data mismatch for user ID {user.id}. Token: {token_data}, DB: email={user.email}, type={user.user_type}")
        # Optional: Maybe update DB user_type if only case differs, but stricter validation is safer.
        # if user.email == token_data.email and user.user_type.upper() == token_data.user_type.upper():
        #     user.user_type = token_data.user_type # Align case
        #     await session.commit()
        # else:
        #     raise credentials_exception
        raise credentials_exception # Be strict for now
        
    logger.debug(f"User authenticated: id={user.id}, email={user.email}, type={user.user_type}")
    return user

# === API Routes ===
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"Attempting login for username: {form_data.username}")
    try:
        user = await authenticate_user(form_data.username, form_data.password, session)
        logger.info(f"Authentication result for {form_data.username}: {'User found' if user else 'User not found or password incorrect'}")
        if not user:
            logger.warning(f"Login failed for {form_data.username}: Incorrect email or password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Ensure user_type is a string before calling upper()
        user_type_value = user.user_type
        if isinstance(user.user_type, Enum): # If it's an Enum member
            user_type_value = user.user_type.value
        
        # Now safely call upper on the string value
        user_type_upper = str(user_type_value).upper()

        logger.info(f"Creating access token for {form_data.username}, user_id: {user.id}, db_user_type: {user.user_type}, token_user_type: {user_type_upper}")
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "user_type": user_type_upper} # Use the uppercased string
        )
        logger.info(f"Token created successfully for {form_data.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_type": user_type_upper # Ensure this matches the expected UserType enum/str for the Token model
        }
    except HTTPException as e: # Re-raise HTTPExceptions
        logger.warning(f"HTTPException during login for {form_data.username}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR during login for {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login."
        )

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
        hashed_password=hashed_password, 
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        user_type=user_data.user_type.upper(), # Ensure uppercase on creation
        phone=user_data.phone,
        address=user_data.address,
        city=user_data.city,
        province=user_data.province,
        postal_code=user_data.postal_code,
        is_email_verified=True
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- User Profile Management Endpoints ---

@router.put("/users/{user_id}/profile", response_model=UserResponse)
async def update_user_profile(
    user_id: int,
    profile_update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"User {current_user.id} attempting to update profile for user {user_id}")
    # Permission Check: User can update their own profile, or admin can update any
    if current_user.id != user_id and not current_user.is_admin:
        logger.warning(f"Permission denied: User {current_user.id} cannot update profile for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile"
        )

    # Fetch the user to update
    user_to_update = await session.get(User, user_id)
    if not user_to_update:
        logger.error(f"User with ID {user_id} not found for profile update.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update fields if they are provided in the request
    update_data = profile_update.dict(exclude_unset=True)
    if not update_data:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    for key, value in update_data.items():
        setattr(user_to_update, key, value)
    
    user_to_update.updated_at = datetime.utcnow()
    
    try:
        await session.commit()
        await session.refresh(user_to_update)
        logger.info(f"Successfully updated profile for user {user_id}")
        return user_to_update
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error updating profile for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update user profile"
        )

@router.post("/users/{user_id}/password")
async def change_user_password(
    user_id: int,
    password_request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"User {current_user.id} attempting to change password for user {user_id}")
    # Permission Check
    if current_user.id != user_id and not current_user.is_admin:
        logger.warning(f"Permission denied: User {current_user.id} cannot change password for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to change this user's password"
        )

    # Fetch the user
    user_to_update = await session.get(User, user_id)
    if not user_to_update:
        logger.error(f"User with ID {user_id} not found for password change.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Hash the new password and update
    user_to_update.hashed_password = get_password_hash(password_request.password)
    user_to_update.updated_at = datetime.utcnow()

    try:
        await session.commit()
        logger.info(f"Successfully changed password for user {user_id}")
        return {"message": "Password updated successfully"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error changing password for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update password"
        )

@router.post("/users/{user_id}/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"User {current_user.id} attempting to upload avatar for user {user_id}")
    # Permission check
    if current_user.id != user_id and not current_user.is_admin:
        logger.warning(f"Permission denied: User {current_user.id} cannot upload avatar for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload avatar for this user"
        )

    # Fetch the user
    user_to_update = await session.get(User, user_id)
    if not user_to_update:
        logger.error(f"User with ID {user_id} not found for avatar upload.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Validate file type (optional but recommended)
    allowed_content_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_content_types:
        logger.error(f"Invalid avatar file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_content_types)}"
        )

    try:
        # Upload to Azure Blob Storage
        avatar_url = await upload_avatar_to_blob(file, user_id)
        
        # Update user profile URL in DB
        user_to_update.profile_image_url = avatar_url
        user_to_update.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(user_to_update)
        logger.info(f"Successfully uploaded avatar and updated profile for user {user_id}")
        
        return AvatarUploadResponse(profile_image_url=avatar_url)

    except ConnectionError as ce:
         logger.error(f"Azure Blob Storage connection error: {ce}")
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="Avatar storage service is unavailable. Please try again later."
         )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error during avatar upload/update for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again."
        )

# # === Email Verification ===
# async def send_verification_email(user: User):
#     token = serializer.dumps(user.email, salt='email-confirm')
#     verification_link = f"http://yourdomain.com/auth/verify-email?token={token}"
#     message = Mail(
#         from_email='no-reply@yourdomain.com',
#         to_emails=user.email,
#         subject='Verify your email',
#         html_content=f'<p>Please verify your email by clicking <a href="{verification_link}">here</a>.</p>'
#     )
#     try:
#         # TODO: Replace with actual SendGrid API key
#         sg = SendGridAPIClient('SENDGRID_API_KEY')
#         response = sg.send(message)
#         logger.info(f"Email sent to {user.email}: {response.status_code}")
#     except Exception as e:
#         logger.error(f"Error sending email: {str(e)}")

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
# @router.post("/resend-verification")
# async def resend_verification(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
#     if not current_user.is_email_verified:
#         await send_verification_email(current_user)
#     return {"message": "Verification email resent successfully"}
