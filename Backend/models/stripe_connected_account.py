"""
Stripe Connected Account Model

Represents a Stripe Express account for landlords to receive rent payments.
Uses Stripe Connect Direct Charges - money flows directly to landlord,
Brikli collects a 2% application fee.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSON
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.rent_payment_transaction import RentPaymentTransaction


class StripeConnectedAccount(SQLModel, table=True):
    """
    Stripe Express account for landlords.
    
    Enables landlords to receive rent payments directly from tenants.
    Brikli never touches the money - funds flow directly from tenant
    to landlord via Stripe Connect Direct Charges.
    """
    __tablename__ = "stripe_connected_accounts"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Link to landlord user
    user_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
    )
    
    # Stripe account ID (acct_xxx)
    stripe_account_id: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True, index=True),
    )
    
    # Onboarding status flags
    charges_enabled: bool = Field(
        default=False,
        description="Whether the account can accept charges",
    )
    payouts_enabled: bool = Field(
        default=False,
        description="Whether the account can receive payouts",
    )
    details_submitted: bool = Field(
        default=False,
        description="Whether the account holder has submitted all required details",
    )
    
    # Account details (cached from Stripe)
    business_type: str | None = Field(
        default=None,
        max_length=50,
        description="Business type: individual or company",
    )
    country: str = Field(
        default="CA",
        max_length=2,
        description="Two-letter country code (ISO 3166-1 alpha-2)",
    )
    default_currency: str = Field(
        default="cad",
        max_length=3,
        description="Default currency for payouts",
    )

    # Payment method configuration
    # Landlords can choose which payment methods to accept from tenants
    # Options: "card" (Credit/Debit - $8 fee), "acss_debit" (PAD Bank Transfer - $3 fee)
    accepted_payment_methods: list[str] = Field(
        default_factory=lambda: ["card", "acss_debit"],
        sa_column=Column(JSON),
        description="List of accepted payment methods: 'card', 'acss_debit'",
    )

    # Requirements and Restrictions (for verification issues)
    disabled_reason: str | None = Field(
        default=None,
        max_length=100,
        description="Why the account is disabled (e.g., 'requirements.past_due', 'rejected.fraud')",
    )
    requirements_currently_due: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of information/documents currently needed from account holder",
    )
    requirements_past_due: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of overdue requirements that must be submitted immediately",
    )
    requirements_eventually_due: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of requirements that will be needed in the future",
    )
    
    # Timestamps
    onboarding_completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When onboarding was completed (charges_enabled became true)",
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
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StripeConnectedAccount.user_id]"}
    )
    
    transactions: list["RentPaymentTransaction"] = Relationship(
        back_populates="connected_account",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @property
    def is_fully_onboarded(self) -> bool:
        """Check if account is fully onboarded and ready to accept payments."""
        return self.charges_enabled and self.payouts_enabled and self.details_submitted

    @property
    def onboarding_status(self) -> str:
        """Human-readable onboarding status."""
        if self.is_fully_onboarded:
            return "active"
        if self.details_submitted:
            return "pending_verification"
        return "incomplete"
    
    @property
    def needs_action(self) -> bool:
        """Check if landlord needs to take action (submit documents/info)."""
        return bool(
            self.requirements_currently_due 
            or self.requirements_past_due
        )
    
    @property
    def has_urgent_requirements(self) -> bool:
        """Check if requirements are overdue (payouts may be disabled)."""
        return bool(self.requirements_past_due)

