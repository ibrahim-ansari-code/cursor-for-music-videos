from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Boolean

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.tenant import Tenant

from Backend.models.enums import UserType

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(
        sa_column=Column(String(36), primary_key=True)
    )
    email: str = Field(unique=True, index=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_type: str = Field(sa_column=Column(String))  # <-- force String instead of Enum
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_email_verified: bool = Field(default=False)

    properties: List["Property"] = Relationship(back_populates="owner")
    
    # Define tenant_details relationship directly
    tenant_details: Optional["Tenant"] = Relationship(back_populates="user")
