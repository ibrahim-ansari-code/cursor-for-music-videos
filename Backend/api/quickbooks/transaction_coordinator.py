"""
Transaction Coordinator for QuickBooks sync operations.

Ensures atomic operations across multiple services to prevent partial sync states.
Implements the Saga pattern for distributed transaction management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Status of a coordinated transaction."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class StepStatus(Enum):
    """Status of individual transaction steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class TransactionStep:
    """Individual step in a coordinated transaction."""
    step_id: str
    name: str
    execute_func: Callable[..., Awaitable[Any]]
    compensate_func: Optional[Callable[..., Awaitable[Any]]] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_result: Any = None


@dataclass
class TransactionResult:
    """Result of a coordinated transaction."""
    transaction_id: str
    status: TransactionStatus
    steps_completed: int
    steps_total: int
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, Exception] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class TransactionCoordinator:
    """
    Coordinates multi-service operations with rollback capability.

    Implements the Saga pattern to ensure atomicity across distributed services
    by maintaining compensating actions for each operation.
    """

    def __init__(self, transaction_id: Optional[str] = None, session: Optional[AsyncSession] = None):
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.session = session
        self.steps: List[TransactionStep] = []
        self.status = TransactionStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

        logger.info("Initialized transaction coordinator: %s", self.transaction_id)

    def add_step(
        self,
        name: str,
        execute_func: Callable[..., Awaitable[Any]],
        compensate_func: Optional[Callable[..., Awaitable[Any]]] = None,
        *args,
        **kwargs
    ) -> str:
        """
        Add a step to the transaction.

        Args:
            name: Human-readable name for the step
            execute_func: Async function to execute
            compensate_func: Optional compensation function for rollback
            *args: Arguments to pass to execute_func
            **kwargs: Keyword arguments to pass to execute_func

        Returns:
            Step ID for tracking
        """
        step_id = f"{len(self.steps) + 1:03d}-{name.lower().replace(' ', '_')}"

        step = TransactionStep(
            step_id=step_id,
            name=name,
            execute_func=execute_func,
            compensate_func=compensate_func,
            args=args,
            kwargs=kwargs
        )

        self.steps.append(step)

        logger.debug(
            "Added step to transaction %s: %s (compensation: %s)",
            self.transaction_id, name, "yes" if compensate_func else "no"
        )

        return step_id

    async def execute(self) -> TransactionResult:
        """
        Execute all steps in the transaction with automatic rollback on failure.

        Returns:
            TransactionResult with execution details
        """
        async with self._lock:
            if self.status != TransactionStatus.PENDING:
                raise ValueError(f"Transaction {self.transaction_id} is not in PENDING state")

            self.status = TransactionStatus.RUNNING
            self.started_at = datetime.now(UTC)

            logger.info(
                "Starting transaction %s with %d steps",
                self.transaction_id, len(self.steps)
            )

        # Track successful steps for potential rollback
        completed_steps: List[TransactionStep] = []
        results: Dict[str, Any] = {}
        errors: Dict[str, Exception] = {}

        try:
            # Execute steps sequentially
            for step in self.steps:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now(UTC)

                logger.info(
                    "Executing step %s: %s [transaction: %s]",
                    step.step_id, step.name, self.transaction_id
                )

                try:
                    # Add session to kwargs if function accepts it and it's not already provided
                    execute_kwargs = step.kwargs.copy()
                    if self.session and 'session' not in execute_kwargs:
                        # Check if function accepts session parameter
                        import inspect
                        sig = inspect.signature(step.execute_func)
                        if 'session' in sig.parameters:
                            execute_kwargs['session'] = self.session

                    # Execute the step
                    step.result = await step.execute_func(*step.args, **execute_kwargs)
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now(UTC)

                    completed_steps.append(step)
                    results[step.step_id] = step.result

                    logger.info(
                        "Completed step %s: %s [transaction: %s]",
                        step.step_id, step.name, self.transaction_id
                    )

                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = e
                    step.completed_at = datetime.now(UTC)
                    errors[step.step_id] = e

                    logger.error(
                        "Step %s failed: %s [transaction: %s] - %s",
                        step.step_id, step.name, self.transaction_id, str(e)
                    )

                    # Report step failure to Sentry
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("transaction_id", self.transaction_id)
                        scope.set_tag("step_id", step.step_id)
                        scope.set_tag("step_name", step.name)
                        scope.set_context("transaction_context", {
                            "steps_completed": len(completed_steps),
                            "steps_total": len(self.steps),
                            "will_compensate": bool(completed_steps)
                        })
                        sentry_sdk.capture_exception(e)

                    # Start compensation for completed steps
                    if completed_steps:
                        await self._compensate_steps(completed_steps)

                    # Mark transaction as failed
                    async with self._lock:
                        self.status = TransactionStatus.FAILED
                        self.completed_at = datetime.now(UTC)

                    return self._create_result(results, errors)

            # All steps completed successfully
            async with self._lock:
                self.status = TransactionStatus.COMPLETED
                self.completed_at = datetime.now(UTC)

            logger.info(
                "Transaction %s completed successfully (%d steps)",
                self.transaction_id, len(self.steps)
            )

            return self._create_result(results, errors)

        except Exception as e:
            logger.exception(
                "Unexpected error in transaction %s execution",
                self.transaction_id
            )

            # Attempt compensation for any completed steps
            if completed_steps:
                await self._compensate_steps(completed_steps)

            async with self._lock:
                self.status = TransactionStatus.FAILED
                self.completed_at = datetime.now(UTC)

            errors["transaction_error"] = e
            return self._create_result(results, errors)

    async def _compensate_steps(self, completed_steps: List[TransactionStep]) -> None:
        """
        Execute compensation functions for completed steps in reverse order.

        Args:
            completed_steps: List of successfully completed steps to compensate
        """
        async with self._lock:
            self.status = TransactionStatus.COMPENSATING

        logger.warning(
            "Starting compensation for transaction %s (%d steps to compensate)",
            self.transaction_id, len(completed_steps)
        )

        compensation_errors = []

        # Compensate in reverse order (LIFO)
        for step in reversed(completed_steps):
            if step.compensate_func is None:
                logger.warning(
                    "No compensation function for step %s: %s",
                    step.step_id, step.name
                )
                continue

            try:
                logger.info(
                    "Compensating step %s: %s [transaction: %s]",
                    step.step_id, step.name, self.transaction_id
                )

                # Prepare compensation kwargs
                compensate_kwargs = step.kwargs.copy()
                if self.session and 'session' not in compensate_kwargs:
                    import inspect
                    sig = inspect.signature(step.compensate_func)
                    if 'session' in sig.parameters:
                        compensate_kwargs['session'] = self.session

                # Add the original result to compensation kwargs if expected
                sig = inspect.signature(step.compensate_func)
                if 'original_result' in sig.parameters:
                    compensate_kwargs['original_result'] = step.result

                step.compensation_result = await step.compensate_func(
                    *step.args, **compensate_kwargs
                )
                step.status = StepStatus.COMPENSATED

                logger.info(
                    "Compensated step %s: %s [transaction: %s]",
                    step.step_id, step.name, self.transaction_id
                )

            except Exception as e:
                compensation_errors.append((step.step_id, e))
                logger.error(
                    "Compensation failed for step %s: %s [transaction: %s] - %s",
                    step.step_id, step.name, self.transaction_id, str(e)
                )

                # Report compensation failure to Sentry
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("transaction_id", self.transaction_id)
                    scope.set_tag("step_id", step.step_id)
                    scope.set_tag("compensation_failure", True)
                    sentry_sdk.capture_exception(e)

        async with self._lock:
            self.status = TransactionStatus.COMPENSATED

        if compensation_errors:
            logger.error(
                "Transaction %s compensation completed with %d errors",
                self.transaction_id, len(compensation_errors)
            )
        else:
            logger.info(
                "Transaction %s compensation completed successfully",
                self.transaction_id
            )

    def _create_result(self, results: Dict[str, Any], errors: Dict[str, Exception]) -> TransactionResult:
        """Create a TransactionResult from execution data."""
        completed_steps = sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)
        duration = None

        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return TransactionResult(
            transaction_id=self.transaction_id,
            status=self.status,
            steps_completed=completed_steps,
            steps_total=len(self.steps),
            results=results,
            errors=errors,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_seconds=duration
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current transaction status for monitoring."""
        return {
            "transaction_id": self.transaction_id,
            "status": self.status.value,
            "steps_total": len(self.steps),
            "steps_completed": sum(1 for step in self.steps if step.status == StepStatus.COMPLETED),
            "steps_failed": sum(1 for step in self.steps if step.status == StepStatus.FAILED),
            "steps_compensated": sum(1 for step in self.steps if step.status == StepStatus.COMPENSATED),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": step.status.value,
                    "has_compensation": step.compensate_func is not None,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": str(step.error) if step.error else None
                }
                for step in self.steps
            ]
        }


# Convenience functions for common sync patterns

async def execute_sync_transaction(
    name: str,
    steps: List[Dict[str, Any]],
    session: Optional[AsyncSession] = None
) -> TransactionResult:
    """
    Execute a sync transaction with the provided steps.

    Args:
        name: Transaction name for logging
        steps: List of step definitions with 'name', 'execute', optional 'compensate'
        session: Database session to pass to functions

    Returns:
        TransactionResult
    """
    coordinator = TransactionCoordinator(session=session)

    for step_def in steps:
        coordinator.add_step(
            name=step_def['name'],
            execute_func=step_def['execute'],
            compensate_func=step_def.get('compensate'),
            **step_def.get('kwargs', {})
        )

    logger.info("Executing sync transaction '%s' with %d steps", name, len(steps))
    return await coordinator.execute()


async def execute_quickbooks_sync(
    user_id: str,
    sync_operations: Dict[str, Callable],
    session: Optional[AsyncSession] = None
) -> TransactionResult:
    """
    Execute QuickBooks sync with automatic rollback on partial failure.

    Args:
        user_id: User ID for the sync operation
        sync_operations: Dict of operation_name -> sync_function
        session: Database session

    Returns:
        TransactionResult
    """
    coordinator = TransactionCoordinator(session=session)

    # Add sync operations as steps
    for operation_name, sync_func in sync_operations.items():
        coordinator.add_step(
            name=f"Sync {operation_name}",
            execute_func=sync_func,
            # Note: Add compensation functions as needed per operation
            user_id=user_id
        )

    logger.info(
        "Executing QuickBooks sync for user %s with operations: %s",
        user_id, list(sync_operations.keys())
    )

    return await coordinator.execute()