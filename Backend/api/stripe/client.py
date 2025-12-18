"""
Async Stripe Client Wrapper

Wraps the synchronous Stripe SDK with async/await support using thread executors.
This prevents blocking FastAPI's event loop when making Stripe API calls.

Industry Standard Pattern:
- Stripe's Python SDK is synchronous (uses requests library)
- Direct calls in async FastAPI handlers block the event loop → 502 errors under load
- Solution: Run Stripe calls in thread pool using anyio.to_thread.run_sync

Usage:
    from Backend.api.stripe.client import stripe_client
    
    # All Stripe operations are now async
    customer = await stripe_client.customers.create(email="user@example.com")
    subscription = await stripe_client.subscriptions.retrieve(sub_id)
"""

import logging
import functools
from typing import Any, Callable, Coroutine, TypeVar
import stripe
from stripe import (
    StripeError,
    APIConnectionError,
    RateLimitError,
    APIError,
)
import anyio
from Backend.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic function wrapping
T = TypeVar('T')


class AsyncStripeClient:
    """
    Async wrapper around Stripe SDK that executes synchronous calls in thread pool.
    
    Architecture:
    - Wraps all Stripe resource managers (customers, subscriptions, etc.)
    - Executes sync calls via anyio.to_thread.run_sync
    - Logs Stripe-Request-Id for support correlation
    - Preserves Stripe SDK's method signatures
    """
    
    def __init__(self, api_key: str):
        """
        Initialize async Stripe client.
        
        Args:
            api_key: Stripe secret key (sk_test_xxx or sk_live_xxx)
        """
        stripe.api_key = api_key
        self._api_key = api_key
        logger.info("✅ Stripe client initialized")
    
    def _make_async(self, func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        """
        Decorator that converts sync Stripe SDK calls to async.
        
        Wraps synchronous Stripe methods to run in thread pool via anyio.
        This prevents blocking the FastAPI event loop.
        
        Args:
            func: Synchronous Stripe SDK method
            
        Returns:
            Async version of the method
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                # Execute sync Stripe call in thread pool
                result = await anyio.to_thread.run_sync(
                    functools.partial(func, *args, **kwargs)
                )
                
                # Log Stripe-Request-Id for support correlation
                if hasattr(result, 'last_response') and result.last_response:
                    request_id = result.last_response.request_id
                    if request_id:
                        logger.info(
                            f"Stripe API call successful | "
                            f"Method: {func.__name__} | "
                            f"Stripe-Request-Id: {request_id}"
                        )
                
                return result
                
            except StripeError as e:
                # Log Stripe errors with request ID for debugging
                request_id = getattr(e, 'request_id', 'unknown')
                logger.error(
                    f"Stripe API error | "
                    f"Method: {func.__name__} | "
                    f"Error: {e.user_message} | "
                    f"Stripe-Request-Id: {request_id}",
                    exc_info=True
                )
                raise
            
        return wrapper
    
    def _wrap_resource(self, resource: Any) -> Any:
        """
        Recursively wrap Stripe resource methods to be async.
        
        Wraps all methods on a Stripe resource (e.g., stripe.Customer)
        to run in thread pool. Handles nested resources (e.g., customer.subscriptions).
        
        Args:
            resource: Stripe resource to wrap
            
        Returns:
            Wrapped resource with async methods
        """
        # Capture parent methods in closure
        make_async = self._make_async
        wrap_resource = self._wrap_resource
        
        class AsyncResourceWrapper:
            def __init__(self, resource):
                self._resource = resource
            
            def __getattr__(self, name: str) -> Any:
                attr = getattr(self._resource, name)
                
                # If it's a callable method, make it async
                if callable(attr):
                    return make_async(attr)
                
                # If it's a nested resource, wrap it recursively
                if hasattr(attr, '__class__') and 'stripe' in str(attr.__class__):
                    return wrap_resource(attr)
                
                return attr
        
        return AsyncResourceWrapper(resource)
    
    @property
    def customers(self):
        """Async Stripe Customer resource"""
        return self._wrap_resource(stripe.Customer)
    
    @property
    def subscriptions(self):
        """Async Stripe Subscription resource"""
        return self._wrap_resource(stripe.Subscription)
    
    @property
    def prices(self):
        """Async Stripe Price resource"""
        return self._wrap_resource(stripe.Price)
    
    @property
    def products(self):
        """Async Stripe Product resource"""
        return self._wrap_resource(stripe.Product)
    
    @property
    def checkout_sessions(self):
        """Async Stripe Checkout Session resource"""
        return self._wrap_resource(stripe.checkout.Session)
    
    @property
    def billing_portal_sessions(self):
        """Async Stripe Billing Portal Session resource"""
        return self._wrap_resource(stripe.billing_portal.Session)
    
    @property
    def invoices(self):
        """Async Stripe Invoice resource"""
        return self._wrap_resource(stripe.Invoice)
    
    @property
    def payment_intents(self):
        """Async Stripe PaymentIntent resource"""
        return self._wrap_resource(stripe.PaymentIntent)
    
    # ========================================================================
    # Stripe Connect Resources (for rent payments)
    # ========================================================================
    
    @property
    def accounts(self):
        """Async Stripe Account resource (Connect)"""
        return self._wrap_resource(stripe.Account)
    
    @property
    def account_links(self):
        """Async Stripe AccountLink resource (Connect onboarding)"""
        return self._wrap_resource(stripe.AccountLink)
    
    @property
    def setup_intents(self):
        """Async Stripe SetupIntent resource (save payment methods)"""
        return self._wrap_resource(stripe.SetupIntent)
    
    @property
    def payment_methods(self):
        """Async Stripe PaymentMethod resource"""
        return self._wrap_resource(stripe.PaymentMethod)
    
    @property
    def transfers(self):
        """Async Stripe Transfer resource (Connect)"""
        return self._wrap_resource(stripe.Transfer)
    
    @property
    def refunds(self):
        """Async Stripe Refund resource"""
        return self._wrap_resource(stripe.Refund)
    
    @property
    def webhook(self):
        """
        Stripe Webhook utilities (signature verification is synchronous, no wrapping needed)
        
        Note: Webhook.construct_event is CPU-bound (HMAC verification), not I/O-bound,
        so we don't need to run it in a thread pool.
        """
        return stripe.Webhook


# ============================================================================
# Global Stripe Client Instance
# ============================================================================

def get_stripe_client() -> AsyncStripeClient:
    """
    Get configured async Stripe client instance.
    
    Returns:
        Configured AsyncStripeClient
        
    Raises:
        RuntimeError: If STRIPE_API_KEY not configured
    """
    if not settings.STRIPE_API_KEY:
        raise RuntimeError(
            "STRIPE_API_KEY not configured. "
            "Add STRIPE_API_KEY to Backend/.env"
        )
    
    return AsyncStripeClient(settings.STRIPE_API_KEY)


# Singleton instance for convenient imports
stripe_client = None

def initialize_stripe_client():
    """Initialize global Stripe client on app startup"""
    global stripe_client
    if settings.STRIPE_API_KEY:
        stripe_client = get_stripe_client()
        logger.info("✅ Global Stripe client initialized")
    else:
        logger.warning(
            "⚠️ STRIPE_API_KEY not configured. "
            "Billing features will not work until configured."
        )


# ============================================================================
# Stripe Error Handling Utilities
# ============================================================================

def format_stripe_error(error: StripeError) -> dict:
    """
    Format Stripe error for consistent API responses.
    
    Args:
        error: Stripe error exception
        
    Returns:
        Formatted error dict with code, message, and request_id
    """
    return {
        "code": error.code or "stripe_error",
        "message": error.user_message or str(error),
        "type": type(error).__name__,
        "request_id": getattr(error, 'request_id', None),
        "param": getattr(error, 'param', None)
    }


def is_retryable_error(error: StripeError) -> bool:
    """
    Check if Stripe error is retryable.
    
    Retryable errors:
    - APIConnectionError: Network issues
    - RateLimitError: Too many requests
    - APIError: Stripe server errors (5xx)
    
    Non-retryable errors:
    - CardError: Payment declined
    - InvalidRequestError: Bad request
    - AuthenticationError: Invalid API key
    
    Args:
        error: Stripe error exception
        
    Returns:
        True if error is retryable, False otherwise
    """
    retryable_types = (
        APIConnectionError,
        RateLimitError,
        APIError,
    )
    return isinstance(error, retryable_types)

