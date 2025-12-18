"""
Rent Payment Dispute Model

Tracks payment disputes (chargebacks) initiated by tenants through their bank/card issuer.
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


class DisputeStatus:
    """Status constants for disputes."""
    WARNING_NEEDS_RESPONSE = "warning_needs_response"  # Inquiry from customer
    WARNING_UNDER_REVIEW = "warning_under_review"      # Reviewing inquiry
    WARNING_CLOSED = "warning_closed"                  # Inquiry closed without chargeback
    NEEDS_RESPONSE = "needs_response"                   # Chargeback filed, response needed
    UNDER_REVIEW = "under_review"                       # Chargeback being reviewed
    CHARGE_REFUNDED = "charge_refunded"                 # Chargeback won by customer
    WON = "won"                                         # Chargeback won by merchant
    LOST = "lost"                                       # Chargeback lost by merchant


class DisputeReason:
    """Reason constants for disputes."""
    BANK_CANNOT_PROCESS = "bank_cannot_process"
    CHECK_RETURNED = "check_returned"
    CREDIT_NOT_PROCESSED = "credit_not_processed"
    CUSTOMER_INITIATED = "customer_initiated"
    DEBIT_NOT_AUTHORIZED = "debit_not_authorized"
    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    GENERAL = "general"
    INCORRECT_ACCOUNT_DETAILS = "incorrect_account_details"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    PRODUCT_NOT_RECEIVED = "product_not_received"
    PRODUCT_UNACCEPTABLE = "product_unacceptable"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    UNRECOGNIZED = "unrecognized"


class RentPaymentDispute(SQLModel, table=True):
    """
    Payment dispute (chargeback) for a rent payment.
    
    Tracks the full lifecycle of a dispute from creation through resolution.
    Disputes can result in the payment being refunded to the tenant.
    """
    __tablename__ = "rent_payment_disputes"

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
    stripe_dispute_id: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True),
        description="Stripe dispute ID (dp_xxx)",
    )
    stripe_charge_id: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Stripe charge ID being disputed",
    )
    
    # Dispute details
    amount_cents: int = Field(
        description="Amount disputed in cents",
    )
    currency: str = Field(
        default="cad",
        max_length=3,
        description="Currency code (ISO 4217)",
    )
    
    # Reason and status
    reason: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Dispute reason from Stripe",
    )
    status: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Current dispute status",
    )
    
    # Evidence and response
    evidence_due_by: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Deadline for submitting evidence",
    )
    evidence_submitted: bool = Field(
        default=False,
        description="Whether evidence has been submitted",
    )
    evidence_submitted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When evidence was submitted",
    )
    
    # Outcome
    is_charge_refundable: bool = Field(
        default=True,
        description="Whether the charge can still be refunded",
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When dispute was created in Stripe",
    )
    closed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When dispute was resolved",
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    
    # Landlord notification tracking
    landlord_notified: bool = Field(
        default=False,
        description="Whether landlord has been notified",
    )
    landlord_notified_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When landlord was notified",
    )

    # Relationships
    transaction: Optional["RentPaymentTransaction"] = Relationship(
        back_populates="disputes",
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentDispute.transaction_id]"}
    )

    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars."""
        return self.amount_cents / 100

    @property
    def is_closed(self) -> bool:
        """Check if dispute is closed."""
        return self.closed_at is not None

    @property
    def needs_attention(self) -> bool:
        """Check if dispute needs action from landlord."""
        return self.status in {
            DisputeStatus.WARNING_NEEDS_RESPONSE,
            DisputeStatus.NEEDS_RESPONSE
        } and not self.evidence_submitted

    @property
    def is_lost(self) -> bool:
        """Check if dispute was lost (tenant won)."""
        return self.status in {DisputeStatus.LOST, DisputeStatus.CHARGE_REFUNDED}

