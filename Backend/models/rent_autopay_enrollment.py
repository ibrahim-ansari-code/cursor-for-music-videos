"""
Rent Autopay Enrollment Model

Tracks autopay settings for automatic recurring rent payments.
Uses the lease's rent_due_day to schedule payments.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant
    from Backend.models.tenant_payment_method import TenantPaymentMethod


class RentAutopayEnrollment(SQLModel, table=True):
    """
    Autopay enrollment for a lease.
    
    When active, automatically initiates rent payment on the lease's
    rent_due_day each month using the selected payment method.
    """
    __tablename__ = "rent_autopay_enrollments"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Links - using ForeignKey inside sa_column
    lease_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("leases.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        description="One autopay enrollment per lease",
    )
    tenant_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        ),
    )
    payment_method_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenant_payment_methods.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    
    # Autopay settings
    is_active: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False),
        description="Whether autopay is currently active",
    )
    amount_cents: int = Field(
        sa_column=Column(Integer, nullable=False),
        description="Amount to charge each period in cents",
    )
    
    # Retry logic
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed payments",
    )
    current_retry_count: int = Field(
        default=0,
        description="Current retry count for this billing period",
    )
    last_attempt_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the last payment attempt was made",
    )
    last_success_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the last successful payment was made",
    )
    last_failure_reason: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Reason for the last failed payment attempt",
    )
    next_scheduled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
        description="When the next autopay attempt is scheduled",
    )
    
    # Lifecycle timestamps
    enrolled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When autopay was first activated",
    )
    paused_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When autopay was paused (if applicable)",
    )
    canceled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When autopay was canceled",
    )
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    lease: Optional["Lease"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentAutopayEnrollment.lease_id]"}
    )
    tenant: Optional["Tenant"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentAutopayEnrollment.tenant_id]"}
    )
    payment_method: Optional["TenantPaymentMethod"] = Relationship(
        back_populates="autopay_enrollments",
        sa_relationship_kwargs={"foreign_keys": "[RentAutopayEnrollment.payment_method_id]"}
    )

    @property
    def amount_dollars(self) -> Decimal:
        """Amount in dollars (for display)."""
        return Decimal(self.amount_cents) / 100

    @property
    def status(self) -> str:
        """Human-readable status."""
        if self.canceled_at:
            return "canceled"
        if self.paused_at and not self.is_active:
            return "paused"
        if self.is_active:
            return "active"
        return "inactive"

    @property
    def can_retry(self) -> bool:
        """Whether we can retry a failed payment."""
        return self.current_retry_count < self.max_retries

    @property
    def has_valid_payment_method(self) -> bool:
        """Check if there's a valid payment method set."""
        return self.payment_method_id is not None
