from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
from decimal import Decimal

from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.invoice_tax_detail import InvoiceTaxDetail
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease
from Backend.models.tenant import Tenant


class InvoiceSchema:
    """Schema for transforming between Brikli Invoice and QuickBooks Invoice."""

    # Status mapping between QuickBooks and Brikli
    STATUS_MAPPING = {
        "Draft": PaymentStatus.DRAFT,
        "SentNotPaid": PaymentStatus.PENDING,
        "Paid": PaymentStatus.PAID,
        "Cancelled": PaymentStatus.VOID,
        "Voided": PaymentStatus.VOID,
        "Accepted": PaymentStatus.PENDING,
        "Closed": PaymentStatus.PAID,
    }

    # Default payment terms mapping
    PAYMENT_TERMS_MAPPING = {
        "Net 15": "Net 15",
        "Net 30": "Net 30",
        "Net 60": "Net 60",
        "Due on receipt": "Due on receipt",
        "COD": "COD",
    }

    @staticmethod
    def to_quickbooks(
        invoice: Invoice,
        tenant: Tenant,
        service_item_id: str,
        tax_code_mapping: Optional[Dict[str, str]] = None,
        payment_terms: str = "Net 30"
    ) -> Dict[str, Any]:
        """Transform Brikli Invoice to QuickBooks Invoice format."""
        lines = []
        line_id = 1

        # Create main service line
        main_line = {
            "Id": str(line_id),
            "LineNum": line_id,
            "Amount": float(invoice.amount),
            "DetailType": "SalesItemLineDetail",
            "SalesItemLineDetail": {
                "ItemRef": {
                    "value": service_item_id
                },
                "Qty": 1,
                "UnitPrice": float(invoice.amount)
            },
            "Description": invoice.description or "Rent Payment"
        }

        # Add tax information to the main line if taxes exist
        if invoice.taxes and tax_code_mapping:
            # For simplicity, use the first tax as the primary tax code
            primary_tax = invoice.taxes[0]
            tax_code_id = tax_code_mapping.get(primary_tax.tax_name)
            if tax_code_id:
                sales_detail = main_line["SalesItemLineDetail"]
                assert isinstance(sales_detail, dict)  # Type narrowing for mypy
                sales_detail["TaxCodeRef"] = {
                    "value": tax_code_id
                }

        lines.append(main_line)
        line_id += 1

        # If there are multiple taxes, add them as separate lines
        if invoice.taxes and len(invoice.taxes) > 1 and tax_code_mapping:
            for tax_detail in invoice.taxes[1:]:
                tax_code_id = tax_code_mapping.get(tax_detail.tax_name)
                if tax_code_id and tax_detail.tax_amount > 0:
                    tax_line = {
                        "Id": str(line_id),
                        "LineNum": line_id,
                        "Amount": float(tax_detail.tax_amount),
                        "DetailType": "SalesItemLineDetail",
                        "SalesItemLineDetail": {
                            "ItemRef": {
                                "value": service_item_id  # Could be a tax item ID
                            },
                            "Qty": 1,
                            "UnitPrice": float(tax_detail.tax_amount),
                            "TaxCodeRef": {
                                "value": tax_code_id
                            }
                        },
                        "Description": f"{tax_detail.tax_name} ({tax_detail.tax_rate}%)"
                    }
                    lines.append(tax_line)
                    line_id += 1

        invoice_data = {
            "Invoice": {
                "DocNumber": invoice.invoice_number,
                "TxnDate": invoice.issue_date.strftime("%Y-%m-%d") if invoice.issue_date else datetime.now().strftime("%Y-%m-%d"),
                "CustomerRef": {
                    "value": tenant.quickbooks_customer_id
                },
                "Line": lines
            }
        }

        # Add due date if available
        if invoice.due_date:
            invoice_data["Invoice"]["DueDate"] = invoice.due_date.strftime("%Y-%m-%d")

        # Add payment terms
        if payment_terms in InvoiceSchema.PAYMENT_TERMS_MAPPING:
            invoice_data["Invoice"]["SalesTermRef"] = {
                "name": payment_terms
            }

        return invoice_data

    @staticmethod
    def from_quickbooks(
        qb_invoice: Dict[str, Any],
        lease: Lease,
        tenant: Tenant,
        tax_code_mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[Invoice, List[InvoiceTaxDetail]]:
        """Transform QuickBooks Invoice to Brikli Invoice with tax details."""
        qb_invoice_id = qb_invoice.get("Id")
        if not qb_invoice_id:
            raise ValueError("QuickBooks invoice missing required 'Id' field")

        # Map status
        raw_status = qb_invoice.get("TxnStatus", "Draft")
        invoice_status = InvoiceSchema.STATUS_MAPPING.get(raw_status, PaymentStatus.DRAFT)

        # Calculate amounts from lines
        lines = qb_invoice.get("Line", [])
        subtotal_amount = Decimal("0")
        total_tax_amount = Decimal("0")
        description_parts = []
        tax_details = []

        # Reverse tax code mapping to identify tax lines
        reverse_tax_mapping = {}
        if tax_code_mapping:
            reverse_tax_mapping = {v: k for k, v in tax_code_mapping.items()}

        for line in lines:
            if line.get("DetailType") == "SalesItemLineDetail":
                line_amount = Decimal(str(line.get("Amount", 0)))
                line_desc = line.get("Description", "")
                sales_detail = line.get("SalesItemLineDetail", {})
                tax_code_ref = sales_detail.get("TaxCodeRef", {})
                tax_code_id = tax_code_ref.get("value")

                # Check if this is a tax line based on description or tax code
                is_tax_line = False
                if tax_code_id and tax_code_id in reverse_tax_mapping:
                    tax_name = reverse_tax_mapping[tax_code_id]
                    is_tax_line = True
                elif any(tax_name in line_desc.upper() for tax_name in ["GST", "PST", "HST", "QST"]):
                    # Try to extract tax name from description
                    tax_name = None
                    for possible_tax in ["GST", "PST", "HST", "QST"]:
                        if possible_tax in line_desc.upper():
                            tax_name = possible_tax
                            is_tax_line = True
                            break

                if is_tax_line and tax_name:
                    total_tax_amount += line_amount
                    # Extract tax rate from description if available
                    tax_rate = Decimal("0")
                    if "(" in line_desc and "%)" in line_desc:
                        try:
                            rate_str = line_desc.split("(")[1].split("%)")[0]
                            tax_rate = Decimal(rate_str)
                        except (IndexError, ValueError):
                            pass

                    tax_details.append({
                        "tax_name": tax_name,
                        "tax_rate": tax_rate,
                        "tax_amount": line_amount
                    })
                else:
                    # Main invoice line
                    subtotal_amount += line_amount
                    if line_desc:
                        description_parts.append(line_desc)

        # Use total amount if lines don't add up (fallback)
        total_amount = Decimal(str(qb_invoice.get("TotalAmt", 0)))
        if subtotal_amount + total_tax_amount != total_amount:
            subtotal_amount = total_amount - total_tax_amount

        description = " | ".join(description_parts) if description_parts else f"Invoice synced from QuickBooks. QB ID: {qb_invoice_id}"

        # Parse dates
        issue_date = datetime.now(UTC)
        if qb_invoice.get("TxnDate"):
            try:
                issue_date = datetime.fromisoformat(qb_invoice["TxnDate"])
            except (ValueError, TypeError):
                pass

        due_date = None
        if qb_invoice.get("DueDate"):
            try:
                due_date = datetime.fromisoformat(qb_invoice["DueDate"])
            except (ValueError, TypeError):
                pass

        invoice = Invoice(
            invoice_number=qb_invoice.get("DocNumber", f"QB-{qb_invoice_id}"),
            amount=total_amount,
            description=description,
            issue_date=issue_date,
            due_date=due_date,
            status=invoice_status,
            tenant_id=tenant.id,
            quickbooks_id=qb_invoice_id,
            last_synced_at=datetime.now(UTC)
        )

        # Create InvoiceTaxDetail objects
        tax_detail_objects = []
        for tax_info in tax_details:
            tax_detail_objects.append(InvoiceTaxDetail(
                tax_name=tax_info["tax_name"],
                tax_rate=tax_info["tax_rate"],
                tax_amount=tax_info["tax_amount"]
            ))

        return invoice, tax_detail_objects

    @staticmethod
    def get_customer_id(qb_invoice: Dict[str, Any]) -> Optional[str]:
        """Extract customer ID from QuickBooks invoice."""
        customer_ref = qb_invoice.get("CustomerRef", {})
        return customer_ref.get("value") if customer_ref else None

    @staticmethod
    def create_list_query(max_results: int = 100, start_position: int = 1) -> Dict[str, Any]:
        """Create query parameters for listing invoices."""
        return {
            "query": f"SELECT * FROM Invoice STARTPOSITION {start_position} MAXRESULTS {max_results}"
        }

    @staticmethod
    def to_quickbooks_update(
        invoice: Invoice,
        tenant: Tenant,
        qb_invoice_id: str,
        sync_token: str,
        service_item_id: str,
        tax_code_mapping: Optional[Dict[str, str]] = None,
        payment_terms: str = "Net 30"
    ) -> Dict[str, Any]:
        """Transform Brikli Invoice to QuickBooks Invoice update format."""
        # Generate the full invoice data using existing method
        invoice_data = InvoiceSchema.to_quickbooks(
            invoice, tenant, service_item_id, tax_code_mapping, payment_terms
        )

        # Add required fields for update
        invoice_data["Invoice"]["Id"] = qb_invoice_id
        invoice_data["Invoice"]["SyncToken"] = sync_token

        return invoice_data

    @staticmethod
    def needs_update(qb_invoice: Dict[str, Any], invoice: Invoice) -> bool:
        """Check if QuickBooks invoice needs to be updated with Brikli invoice data."""
        # Compare amounts
        current_total = Decimal(str(qb_invoice.get("TotalAmt", 0)))
        expected_total = invoice.amount

        # Compare status
        current_status = qb_invoice.get("TxnStatus", "Draft")
        expected_status = None
        for qb_status, brikli_status in InvoiceSchema.STATUS_MAPPING.items():
            if brikli_status == invoice.status:
                expected_status = qb_status
                break

        # Compare dates
        current_issue_date = None
        current_due_date = None

        if qb_invoice.get("TxnDate"):
            try:
                current_issue_date = datetime.fromisoformat(qb_invoice["TxnDate"])
            except (ValueError, TypeError):
                pass

        if qb_invoice.get("DueDate"):
            try:
                current_due_date = datetime.fromisoformat(qb_invoice["DueDate"])
            except (ValueError, TypeError):
                pass

        # Compare descriptions from first line
        current_description = ""
        lines = qb_invoice.get("Line", [])
        if lines:
            current_description = lines[0].get("Description", "")

        return (
            current_total != expected_total or
            (expected_status is not None and current_status != expected_status) or
            (current_issue_date is not None and invoice.issue_date is not None and current_issue_date.date() != invoice.issue_date.date()) or
            (current_due_date is not None and invoice.due_date is not None and current_due_date.date() != invoice.due_date.date()) or
            (invoice.description is not None and invoice.description not in current_description)
        )

    @staticmethod
    def validate_for_quickbooks(invoice: Invoice, tenant: Tenant) -> Dict[str, str]:
        """
        Validate invoice data for QuickBooks sync and return any issues.

        Returns:
            Dict with validation errors, empty if valid
        """
        errors = {}

        # Check required fields
        if not invoice.amount or invoice.amount <= 0:
            errors["amount"] = "Invoice amount must be greater than zero"

        if not invoice.issue_date:
            errors["issue_date"] = "Invoice issue date is required"

        if not invoice.invoice_number or not invoice.invoice_number.strip():
            errors["invoice_number"] = "Invoice number is required"

        if not tenant.quickbooks_customer_id:
            errors["tenant"] = "Tenant must be synced to QuickBooks first"

        # Validate due date is after issue date
        if invoice.due_date and invoice.issue_date and invoice.due_date < invoice.issue_date:
            errors["due_date"] = "Due date must be on or after issue date"

        # Validate tax details if present
        if invoice.taxes:
            total_tax = sum(tax.tax_amount for tax in invoice.taxes)
            # For invoices, tax might be included in amount or separate
            # This validation might need adjustment based on business logic
            if total_tax < 0:
                errors["taxes"] = "Tax amounts cannot be negative"

        return errors

    @staticmethod
    def get_canadian_tax_codes() -> Dict[str, str]:
        """
        Return default Canadian tax code names for common taxes.

        Note: These would need to be mapped to actual QuickBooks tax code IDs
        based on the user's tax setup.
        """
        return {
            "GST": "GST",
            "PST": "PST",
            "HST": "HST",
            "QST": "QST",  # Quebec Sales Tax
            "No Tax": "NON",  # Non-taxable
        }