"""
Rent Payment Transaction Model

Tracks all rent payment attempts via Stripe Connect Direct Charges.
Links to the existing payments table once a transaction succeeds.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.accounting.payment import Payment
    from Backend.models.lease import Lease
    from Backend.models.tenant import Tenant
    from Backend.models.user import User
    from Backend.models.stripe_connected_account import StripeConnectedAccount
    from Backend.models.tenant_payment_method import TenantPaymentMethod
    from Backend.models.rent_payment_refund import RentPaymentRefund
    from Backend.models.rent_payment_dispute import RentPaymentDispute


class RentPaymentTransactionStatus:
    """Status constants for rent payment transactions."""
    PENDING = "pending"
    REQUIRES_ACTION = "requires_action"
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"

    @classmethod
    def terminal_statuses(cls) -> set[str]:
        """Statuses that indicate the transaction is complete."""
        return {cls.SUCCEEDED, cls.FAILED, cls.CANCELED, cls.REFUNDED, cls.PARTIALLY_REFUNDED}

    @classmethod
    def active_statuses(cls) -> set[str]:
        """Statuses that indicate the transaction is still in progress."""
        return {cls.PENDING, cls.REQUIRES_ACTION, cls.REQUIRES_PAYMENT_METHOD, cls.PROCESSING}


class RentPaymentTransaction(SQLModel, table=True):
    """
    Rent payment transaction via Stripe Connect.
    
    Tracks the full lifecycle of a rent payment from initiation to completion.
    On success, a corresponding record is created in the payments table
    so landlords see online payments alongside manual entries.
    """
    __tablename__ = "rent_payment_transactions"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Links to existing system - using simple Field with foreign_key for non-sa_column fields
    payment_id: int | None = Field(
        default=None,
        foreign_key="payments.id",
        description="Created in payments table once transaction succeeds",
    )
    
    # Fields with sa_column need ForeignKey inside the Column
    lease_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("leases.id"),
            nullable=False,
            index=True,
        ),
    )
    tenant_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        ),
    )
    landlord_user_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
    )
    connected_account_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("stripe_connected_accounts.id"),
            nullable=True,
        ),
    )
    payment_method_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenant_payment_methods.id"),
            nullable=True,
        ),
    )
    
    # Stripe references
    stripe_payment_intent_id: str | None = Field(
        default=None,
        sa_column=Column(String(255), unique=True, index=True),
        description="Stripe PaymentIntent ID (pi_xxx)",
    )
    stripe_charge_id: str | None = Field(
        default=None,
        max_length=255,
        description="Stripe Charge ID (ch_xxx)",
    )
    receipt_url: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Stripe receipt URL for successful charges",
    )
    
    # Amounts (stored in cents for precision)
    amount_cents: int = Field(
        sa_column=Column(Integer, nullable=False),
        description="Payment amount in cents (e.g., 150000 = $1,500.00)",
    )
    application_fee_cents: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Platform fee in cents (flat fee: $3 PAD, $8 card)",
    )
    currency: str = Field(
        default="cad",
        max_length=3,
        description="Three-letter ISO currency code",
    )
    
    # Status tracking
    status: str = Field(
        default=RentPaymentTransactionStatus.PENDING,
        sa_column=Column(String(50), nullable=False, index=True),
        description="Current transaction status",
    )
    failure_code: str | None = Field(
        default=None,
        max_length=100,
        description="Stripe failure code if payment failed",
    )
    failure_message: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Human-readable failure message",
    )
    
    # Payment method details (denormalized for historical record)
    payment_method_type: str | None = Field(
        default=None,
        max_length=50,
        description="acss_debit or card",
    )
    payment_method_last_four: str | None = Field(
        default=None,
        max_length=4,
    )
    payment_method_bank_name: str | None = Field(
        default=None,
        max_length=255,
    )
    
    # Timestamps
    initiated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    authorized_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    succeeded_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    refunded_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
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
    payment: Optional["Payment"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.payment_id]"}
    )
    lease: Optional["Lease"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.lease_id]"}
    )
    tenant: Optional["Tenant"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.tenant_id]"}
    )
    landlord: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.landlord_user_id]"}
    )
    connected_account: Optional["StripeConnectedAccount"] = Relationship(
        back_populates="transactions",
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.connected_account_id]"}
    )
    payment_method: Optional["TenantPaymentMethod"] = Relationship(
        back_populates="transactions",
        sa_relationship_kwargs={"foreign_keys": "[RentPaymentTransaction.payment_method_id]"}
    )
    refunds: list["RentPaymentRefund"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    disputes: list["RentPaymentDispute"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def amount_dollars(self) -> Decimal:
        """Amount in dollars (for display)."""
        return Decimal(self.amount_cents) / 100

    @property
    def application_fee_dollars(self) -> Decimal:
        """Application fee in dollars (for display)."""
        return Decimal(self.application_fee_cents) / 100

    @property
    def landlord_receives_cents(self) -> int:
        """Amount landlord receives after platform fee (before Stripe fees)."""
        return self.amount_cents - self.application_fee_cents

    @property
    def is_terminal(self) -> bool:
        """Whether the transaction has reached a final state."""
        return self.status in RentPaymentTransactionStatus.terminal_statuses()

    @property
    def is_successful(self) -> bool:
        """Whether the payment was successful."""
        return self.status == RentPaymentTransactionStatus.SUCCEEDED

    @property
    def total_refunded_cents(self) -> int:
        """Total amount refunded for this transaction."""
        if not self.refunds:
            return 0
        from Backend.models.rent_payment_refund import RefundStatus
        return sum(
            r.amount_cents
            for r in self.refunds
            if r.status == RefundStatus.SUCCEEDED
        )

    @property
    def net_amount_cents(self) -> int:
        """Net amount after refunds."""
        return self.amount_cents - self.total_refunded_cents

    @property
    def has_active_dispute(self) -> bool:
        """Whether this transaction has an active dispute."""
        if not self.disputes:
            return False
        from Backend.models.rent_payment_dispute import DisputeStatus
        return any(
            d.status not in {DisputeStatus.WON, DisputeStatus.LOST, DisputeStatus.WARNING_CLOSED}
            for d in self.disputes
        )
