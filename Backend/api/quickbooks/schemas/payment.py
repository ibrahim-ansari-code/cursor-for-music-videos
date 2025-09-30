from typing import Dict, Any, Optional
from datetime import datetime, UTC
from decimal import Decimal

from Backend.models.accounting.payment import Payment, PaymentMethod, PaymentStatus
from Backend.models.lease import Lease
from Backend.models.tenant import Tenant


class PaymentSchema:
    """Schema for transforming between Brikli Payment and QuickBooks Payment."""

    # Comprehensive payment method mapping between QuickBooks and Brikli (Canadian context)
    PAYMENT_METHOD_MAPPING = {
        "Cash": PaymentMethod.CASH,
        "Check": PaymentMethod.CHECK,
        "CreditCard": PaymentMethod.CREDIT_CARD,
        "DebitCard": PaymentMethod.DEBIT_CARD,
        "BankTransfer": PaymentMethod.BANK_TRANSFER,
        "WireTransfer": PaymentMethod.WIRE_TRANSFER,
        "EFT": PaymentMethod.DIRECT_DEPOSIT,  # Electronic Funds Transfer
        "ACH": PaymentMethod.DIRECT_DEPOSIT,  # Automated Clearing House
        "Other": PaymentMethod.OTHER,
        "InteracTransfer": PaymentMethod.INTERAC_E_TRANSFER,  # Custom mapping
        "ElectronicPayment": PaymentMethod.INTERAC_E_TRANSFER,  # Generic electronic
    }

    # Reverse mapping for Brikli to QuickBooks (Canadian-focused)
    REVERSE_PAYMENT_METHOD_MAPPING = {
        PaymentMethod.CASH: "Cash",
        PaymentMethod.CHECK: "Check",
        PaymentMethod.CREDIT_CARD: "CreditCard",
        PaymentMethod.DEBIT_CARD: "DebitCard",
        PaymentMethod.BANK_TRANSFER: "BankTransfer",
        PaymentMethod.WIRE_TRANSFER: "WireTransfer",
        PaymentMethod.DIRECT_DEPOSIT: "EFT",
        PaymentMethod.INTERAC_E_TRANSFER: "InteracTransfer",  # Canadian-specific
        PaymentMethod.BANK_DRAFT: "Check",  # Map to closest equivalent
        PaymentMethod.PAYPAL: "Other",
        PaymentMethod.INTERNAL_TRANSFER: "BankTransfer",
        PaymentMethod.OTHER: "Other",
    }

    @staticmethod
    def to_quickbooks(payment: Payment, tenant: Tenant, deposit_account_id: Optional[str] = None) -> Dict[str, Any]:
        """Transform Brikli Payment to QuickBooks Payment format."""
        # Map payment method to QuickBooks format
        qb_payment_method = PaymentSchema.REVERSE_PAYMENT_METHOD_MAPPING.get(
            payment.payment_method, "Other"
        )

        # Calculate total amount including any reductions
        total_amt = float(payment.amount)

        payment_data = {
            "Payment": {
                "TotalAmt": total_amt,
                "TxnDate": payment.payment_date.strftime("%Y-%m-%d") if payment.payment_date else datetime.now().strftime("%Y-%m-%d"),
                "CustomerRef": {
                    "value": tenant.quickbooks_id
                },
                "PaymentMethodRef": {
                    "name": qb_payment_method
                }
            }
        }

        # Add deposit account if provided (which bank account received the payment)
        if deposit_account_id:
            payment_data["Payment"]["DepositToAccountRef"] = {
                "value": deposit_account_id
            }

        # Add reference number if available
        if payment.transaction_reference:
            payment_data["Payment"]["PaymentRefNum"] = str(payment.transaction_reference)

        # Create comprehensive private note
        note_parts = []
        if payment.description:
            note_parts.append(payment.description)
        else:
            note_parts.append("Payment from Brikli")

        # Add reduction info if applicable
        if payment.reduction_amount and payment.reduction_amount > 0:
            reduction_note = f"Original amount: ${float(payment.amount + payment.reduction_amount):.2f}, Reduction: ${float(payment.reduction_amount):.2f}"
            if payment.reduction_reason:
                reduction_note += f" ({payment.reduction_reason})"
            note_parts.append(reduction_note)

        payment_data["Payment"]["PrivateNote"] = " | ".join(note_parts)

        return payment_data

    @staticmethod
    def from_quickbooks(qb_payment: Dict[str, Any], lease: Lease, tenant: Tenant) -> Payment:
        """Transform QuickBooks Payment to Brikli Payment."""
        qb_payment_id = qb_payment.get("Id")
        if not qb_payment_id:
            raise ValueError("QuickBooks payment missing required 'Id' field")

        # Parse amount
        total_amount = Decimal(str(qb_payment.get("TotalAmt", 0)))
        unapplied_amount = Decimal(str(qb_payment.get("UnappliedAmt", 0)))

        # Parse payment date
        payment_date = datetime.now(UTC)
        txn_date = qb_payment.get("TxnDate")
        if txn_date:
            try:
                payment_date = datetime.fromisoformat(txn_date) if isinstance(txn_date, str) else txn_date
            except (ValueError, TypeError):
                pass

        # Map payment method
        payment_method_ref = qb_payment.get("PaymentMethodRef", {})
        qb_payment_method = payment_method_ref.get("name", "Other")
        payment_method = PaymentSchema.PAYMENT_METHOD_MAPPING.get(qb_payment_method, PaymentMethod.OTHER)

        # Extract reference number
        transaction_reference = qb_payment.get("PaymentRefNum")

        # Create description with more context
        description_parts = []
        private_note = qb_payment.get("PrivateNote")
        if private_note and "Payment from Brikli" not in private_note:
            description_parts.append(private_note)

        description_parts.append(f"Synced from QuickBooks (ID: {qb_payment_id})")

        if unapplied_amount > 0:
            description_parts.append(f"Unapplied amount: ${float(unapplied_amount):.2f}")

        description = " | ".join(description_parts)

        return Payment(
            amount=total_amount,
            payment_date=payment_date,
            status=PaymentStatus.PAID,  # QuickBooks payments are confirmed
            description=description,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            lease_id=lease.id,
            tenant_id=tenant.id,
            quickbooks_id=qb_payment_id,
            last_synced_at=datetime.now(UTC)
        )

    @staticmethod
    def get_customer_id(qb_payment: Dict[str, Any]) -> Optional[str]:
        """Extract customer ID from QuickBooks payment."""
        customer_ref = qb_payment.get("CustomerRef", {})
        return customer_ref.get("value") if customer_ref else None

    @staticmethod
    def create_list_query(max_results: int = 100, start_position: int = 1) -> Dict[str, Any]:
        """Create query parameters for listing payments."""
        return {
            "query": f"SELECT * FROM Payment STARTPOSITION {start_position} MAXRESULTS {max_results}"
        }

    @staticmethod
    def add_invoice_link(payment_data: Dict[str, Any], invoice_quickbooks_id: str) -> Dict[str, Any]:
        """Add invoice link to payment data."""
        payment_data["Payment"]["Line"] = [
            {
                "Amount": payment_data["Payment"]["TotalAmt"],
                "LinkedTxn": [
                    {
                        "TxnId": invoice_quickbooks_id,
                        "TxnType": "Invoice"
                    }
                ]
            }
        ]
        return payment_data

    @staticmethod
    def to_quickbooks_update(payment: Payment, tenant: Tenant, qb_payment_id: str, sync_token: str, deposit_account_id: Optional[str] = None) -> Dict[str, Any]:
        """Transform Brikli Payment to QuickBooks Payment update format."""
        # Generate the full payment data using existing method
        payment_data = PaymentSchema.to_quickbooks(payment, tenant, deposit_account_id)

        # Add required fields for update
        payment_data["Payment"]["Id"] = qb_payment_id
        payment_data["Payment"]["SyncToken"] = sync_token

        return payment_data

    @staticmethod
    def needs_update(qb_payment: Dict[str, Any], payment: Payment) -> bool:
        """Check if QuickBooks payment needs to be updated with Brikli payment data."""
        current_amount = Decimal(str(qb_payment.get("TotalAmt", 0)))
        current_method = qb_payment.get("PaymentMethodRef", {}).get("name", "Other")
        current_ref_num = qb_payment.get("PaymentRefNum", "")
        current_note = qb_payment.get("PrivateNote", "")

        # Parse current payment date
        current_date = None
        txn_date = qb_payment.get("TxnDate")
        if txn_date:
            try:
                current_date = datetime.fromisoformat(txn_date) if isinstance(txn_date, str) else txn_date
            except (ValueError, TypeError):
                pass

        # Expected values from Brikli payment
        expected_amount = payment.amount
        expected_method = PaymentSchema.REVERSE_PAYMENT_METHOD_MAPPING.get(payment.payment_method, "Other")
        expected_ref_num = str(payment.transaction_reference) if payment.transaction_reference else ""
        expected_date = payment.payment_date

        # Compare relevant fields
        return (
            current_amount != expected_amount or
            current_method != expected_method or
            current_ref_num != expected_ref_num or
            (current_date is not None and expected_date is not None and current_date.date() != expected_date.date()) or
            ("Payment from Brikli" not in current_note and payment.description is not None and payment.description not in current_note)
        )

    @staticmethod
    def validate_for_quickbooks(payment: Payment, tenant: Tenant) -> Dict[str, str]:
        """
        Validate payment data for QuickBooks sync and return any issues.

        Returns:
            Dict with validation errors, empty if valid
        """
        errors = {}

        # Check required fields
        if not payment.amount or payment.amount <= 0:
            errors["amount"] = "Payment amount must be greater than zero"

        if not payment.payment_date:
            errors["payment_date"] = "Payment date is required"

        if not tenant.quickbooks_id:
            errors["tenant"] = "Tenant must be synced to QuickBooks first"

        # Validate payment method
        if payment.payment_method not in PaymentSchema.REVERSE_PAYMENT_METHOD_MAPPING:
            errors["payment_method"] = f"Unsupported payment method: {payment.payment_method}"

        # Validate reduction logic
        if payment.reduction_amount and payment.reduction_amount > payment.amount:
            errors["reduction_amount"] = "Reduction amount cannot exceed payment amount"

        if payment.reduction_amount and payment.reduction_amount > 0 and not payment.reduction_reason:
            errors["reduction_reason"] = "Reduction reason required when reduction amount is provided"

        return errors