"""
Tenant Payment Method Model

Stores saved payment methods (PAD bank accounts, cards) for tenants.
Used for one-time and recurring rent payments.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.tenant import Tenant
    from Backend.models.rent_payment_transaction import RentPaymentTransaction
    from Backend.models.rent_autopay_enrollment import RentAutopayEnrollment


class TenantPaymentMethod(SQLModel, table=True):
    """
    Saved payment method for a tenant.
    
    Supports:
    - acss_debit: Canadian Pre-authorized Debit (PAD)
    - card: Credit/debit cards
    """
    __tablename__ = "tenant_payment_methods"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Link to tenant
    tenant_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    
    # Stripe payment method ID (pm_xxx)
    stripe_payment_method_id: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True),
    )
    
    # Type info
    payment_method_type: str = Field(
        sa_column=Column(String(50), nullable=False),
        description="Payment method type: acss_debit or card",
    )
    
    # Display info (common)
    last_four: str | None = Field(
        default=None,
        max_length=4,
        description="Last 4 digits of account/card number",
    )
    
    # Bank account specific (PAD)
    bank_name: str | None = Field(
        default=None,
        max_length=255,
        description="Bank name for display",
    )
    institution_number: str | None = Field(
        default=None,
        max_length=10,
        description="Canadian financial institution number",
    )
    
    # Card specific
    brand: str | None = Field(
        default=None,
        max_length=50,
        description="Card brand: visa, mastercard, amex, etc.",
    )
    exp_month: int | None = Field(
        default=None,
        description="Card expiry month (1-12)",
    )
    exp_year: int | None = Field(
        default=None,
        description="Card expiry year (4 digits)",
    )
    
    # Status
    is_default: bool = Field(
        default=False,
        description="Whether this is the tenant's default payment method",
    )
    is_verified: bool = Field(
        default=False,
        description="For PAD: whether microdeposit verification is complete",
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    tenant: Optional["Tenant"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[TenantPaymentMethod.tenant_id]"}
    )
    
    transactions: list["RentPaymentTransaction"] = Relationship(
        back_populates="payment_method",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    
    autopay_enrollments: list["RentAutopayEnrollment"] = Relationship(
        back_populates="payment_method",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @property
    def display_name(self) -> str:
        """Human-readable display name for the payment method."""
        if self.payment_method_type == "card":
            brand_display = (self.brand or "Card").title()
            return f"{brand_display} •••• {self.last_four}"
        elif self.payment_method_type == "acss_debit":
            bank_display = self.bank_name or "Bank Account"
            return f"{bank_display} •••• {self.last_four}"
        return f"Payment Method •••• {self.last_four}"

    @property
    def is_expired(self) -> bool:
        """Check if card is expired (only applicable to cards)."""
        if self.payment_method_type != "card":
            return False
        if not self.exp_month or not self.exp_year:
            return False
        
        from datetime import date
        today = date.today()
        # Card is valid through the last day of the expiry month
        return (self.exp_year < today.year or 
                (self.exp_year == today.year and self.exp_month < today.month))

    @property
    def is_usable(self) -> bool:
        """Check if payment method can be used for payments."""
        if self.payment_method_type == "acss_debit":
            return self.is_verified
        elif self.payment_method_type == "card":
            return not self.is_expired
        return True

