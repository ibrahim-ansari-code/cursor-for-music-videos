"""
Webhook Handlers for Rent Payments

Modular webhook event handlers organized by domain:
- Payment Intent events
- Charge events
- Dispute events
- Refund events
- Payment Method events
- Connect Account events
"""

from .payment_intent_handlers import (
    handle_payment_intent_succeeded,
    handle_payment_intent_failed,
    handle_payment_intent_canceled,
    handle_payment_intent_processing,
    handle_payment_intent_requires_action,
    handle_payment_intent_amount_capturable_updated,
    handle_payment_intent_partially_funded,
)

from .charge_handlers import (
    handle_charge_succeeded,
    handle_charge_failed,
    handle_charge_pending,
    handle_charge_expired,
    handle_charge_refunded,
    handle_charge_updated,
)

from .dispute_handlers import (
    handle_dispute_created,
    handle_dispute_updated,
    handle_dispute_closed,
    handle_dispute_funds_withdrawn,
    handle_dispute_funds_reinstated,
)

from .refund_handlers import (
    handle_refund_created,
    handle_refund_updated,
    handle_refund_failed,
)

from .payment_method_handlers import (
    handle_payment_method_attached,
    handle_payment_method_updated,
    handle_payment_method_detached,
    handle_setup_intent_succeeded,
)

from .connect_handlers import (
    handle_account_updated,
)

__all__ = [
    # Payment Intent handlers
    "handle_payment_intent_succeeded",
    "handle_payment_intent_failed",
    "handle_payment_intent_canceled",
    "handle_payment_intent_processing",
    "handle_payment_intent_requires_action",
    "handle_payment_intent_amount_capturable_updated",
    "handle_payment_intent_partially_funded",
    # Charge handlers
    "handle_charge_succeeded",
    "handle_charge_failed",
    "handle_charge_pending",
    "handle_charge_expired",
    "handle_charge_refunded",
    "handle_charge_updated",
    # Dispute handlers
    "handle_dispute_created",
    "handle_dispute_updated",
    "handle_dispute_closed",
    "handle_dispute_funds_withdrawn",
    "handle_dispute_funds_reinstated",
    # Refund handlers
    "handle_refund_created",
    "handle_refund_updated",
    "handle_refund_failed",
    # Payment Method handlers
    "handle_payment_method_attached",
    "handle_payment_method_updated",
    "handle_payment_method_detached",
    "handle_setup_intent_succeeded",
    # Connect handlers
    "handle_account_updated",
]

