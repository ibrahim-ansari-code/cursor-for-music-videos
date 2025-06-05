"""Defines the User SQLModel, representing users within the application, including their attributes and relationships."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.property import Property
    from Backend.models.tenant import Tenant


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True)
    )
    email: str = Field(unique=True, index=True)
    first_name: str | None = None
    last_name: str | None = None
    # <-- force String instead of Enum
    user_type: str = Field(sa_column=Column(String))
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    profile_image_url: str | None = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=create_audit_datetime)
    updated_at: datetime = Field(default_factory=create_audit_datetime)
    is_email_verified: bool = Field(default=False)

    properties: list["Property"] = Relationship(back_populates="owner")

    # Define tenant_details relationship directly
    tenant_details: Optional["Tenant"] = Relationship(back_populates="user")
