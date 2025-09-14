"""
Constants for Azure AI streaming event types and SSE message types
"""

# Event type constants
class StreamEventTypes:
    """Constants for Azure AI streaming event types"""
    MESSAGE_DELTA = 'thread.message.delta'
    RUN_CREATED = 'thread.run.created'
    RUN_QUEUED = 'thread.run.queued'
    RUN_IN_PROGRESS = 'thread.run.in_progress'
    RUN_COMPLETED = 'thread.run.completed'
    RUN_REQUIRES_ACTION = 'thread.run.requires_action'
    MESSAGE_COMPLETED = 'thread.message.completed'
    RUN_FAILED = 'thread.run.failed'
    RUN_CANCELLED = 'thread.run.cancelled'

# SSE message type constants
class SSEMessageTypes:
    """Constants for Server-Sent Event message types"""
    CONTENT = 'content'
    STATUS = 'status'
    DONE = 'done'
    ERROR = 'error'