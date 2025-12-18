"""
Rent Payment Refund Model

Tracks all refunds issued for rent payments, including partial and full refunds.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.rent_payment_transaction import RentPaymentTransaction
    from Backend.models.user import User


class RefundStatus:
    """Status constants for refunds."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class RefundReason:
    """Reason constants for refunds."""
    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"
    RENT_ADJUSTMENT = "rent_adjustment"
    LEASE_CANCELLATION = "lease_cancellation"
    OVERPAYMENT = "overpayment"
    OTHER = "other"


class RentPaymentRefund(SQLModel, table=True):
    """
    Refund issued for a rent payment transaction.
    
    Supports both full and partial refunds. Refunds are initiated by landlords
    via the portal and processed through Stripe.
    """
    __tablename__ = "rent_payment_refunds"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Link to transaction
    transaction_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("rent_payment_transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    
    # Stripe IDs
    stripe_refund_id: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True),
        description="Stripe refund ID (re_xxx)",
    )
    stripe_charge_id: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Stripe charge ID this refund is for",
    )
    
    # Refund details
    amount_cents: int = Field(
        description="Amount refunded in cents",
    )
    currency: str = Field(
        default="cad",
        max_length=3,
        description="Currency code (ISO 4217)",
    )
    
    # Reason and notes
    reason: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Refund reason (duplicate, fraudulent, requested_by_customer, etc.)",
    )
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Additional notes from landlord",
    )
    
    # Status tracking
    status: str = Field(
        sa_column=Column(String(50), nullable=False),
        description="Refund status (pending, succeeded, failed)",
    )
    failure_reason: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Reason for failure if status is failed",
    )
    
    # Application fee refund
    application_fee_refunded_cents: int | None = Field(
        default=None,
        description="Amount of Brikli platform fee that was refunded",
    )
    
    # Who initiated the refund
    initiated_by_user_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=False,
        ),
        description="Landlord who initiated the refund",
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    succeeded_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When the refund completed successfully",
    )
    failed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When the refund failed",
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    transaction: Optional["RentPaymentTransaction"] = Relationship(
        back_populates="refunds",
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentRefund.transaction_id]"}
    )
    
    initiated_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentRefund.initiated_by_user_id]"}
    )

    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars."""
        return self.amount_cents / 100

    @property
    def is_complete(self) -> bool:
        """Check if refund is in a terminal state."""
        return self.status in {RefundStatus.SUCCEEDED, RefundStatus.FAILED, RefundStatus.CANCELED}

