from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text, Index
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from Backend.models.accounting.integration import Integration

logger = logging.getLogger(__name__)


class QuickBooksIntegration(SQLModel, table=True):
    """
    Provider-specific storage for Intuit (QuickBooks Online) OAuth tokens and metadata.

    One-to-one with `integrations.id` when `integration_type=QUICKBOOKS`.
    """

    __tablename__ = "quickbooks_integrations"  # type: ignore

    # Primary key is the foreign key to `integrations.id` to enforce 1:1
    integration_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("integrations.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    # Intuit/QBO identifiers and tokens (encrypted at rest via app utilities)
    realm_id: str = Field(sa_column=Column(String, nullable=False))
    access_token_encrypted: str = Field(sa_column=Column(String, nullable=False))
    refresh_token_encrypted: str = Field(sa_column=Column(String, nullable=False))
    access_token_expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    refresh_token_expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    scope: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    # Optional cached metadata
    company_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    last_token_refresh_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
    )

    # Extension table relationship - remove for now to isolate the issue
    # integration: "Integration" = Relationship(
    #     back_populates="quickbooks_details",
    #     sa_relationship_kwargs={"lazy": "select"}
    # )


# Helpful indexes mirror the SQL migration
Index("idx_quickbooks_integrations_realm_id", Column("realm_id", String))
Index("idx_quickbooks_integrations_access_expiry", Column("access_token_expires_at", DateTime(timezone=True)))


