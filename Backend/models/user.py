from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, ForeignKey
from sqlalchemy.sql import join

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant

from Backend.models.enums import UserType

class User(SQLModel, table=True):
    __tablename__ = "users"

    # Use UUID from Supabase Auth as primary key
    id: UUID = Field(sa_column=Column(String(36), primary_key=True))  # UUID stored as string in PostgreSQL
    email: str = Field(unique=True, index=True)
    first_name: str
    last_name: str
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
    tenant_details: Optional["Tenant"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin": "User.id==Tenant.user_id", # Specify join condition
            "lazy": "selectin",
            "uselist": False # Indicate one-to-one or one-to-zero/one
        }
    )
