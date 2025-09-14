"""
SSE (Server-Sent Events) formatting utilities for streaming responses
"""
import json
from typing import List

from .constants import SSEMessageTypes, StreamEventTypes


class SSEFormatter:
    """
    Handles formatting of Server-Sent Events for streaming responses

    This class provides methods to format various types of messages
    as SSE-compliant data strings for real-time communication with clients.
    """

    @staticmethod
    def format_content(content: str) -> str:
        """Format content chunk as SSE message"""
        return f"data: {json.dumps({'type': SSEMessageTypes.CONTENT, 'content': content})}\n\n"

    @staticmethod
    def format_status(status: str) -> str:
        """Format status update as SSE message"""
        return f"data: {json.dumps({'type': SSEMessageTypes.STATUS, 'status': status})}\n\n"


    @staticmethod
    def format_done(total_content: str) -> str:
        """Format completion message as SSE"""
        return f"data: {json.dumps({'type': SSEMessageTypes.DONE, 'total_content': total_content})}\n\n"

    @staticmethod
    def format_error(error_message: str) -> str:
        """Format error message as SSE"""
        return f"data: {json.dumps({'type': SSEMessageTypes.ERROR, 'error': error_message})}\n\n"


class EventFilter:
    """
    Provides categorized lists of Azure AI streaming event types

    This class helps organize and filter different types of events
    that may occur during Azure AI streaming operations.
    """

    @staticmethod
    def get_status_events() -> List[str]:
        """Get list of status event types"""
        return [
            StreamEventTypes.RUN_CREATED,
            StreamEventTypes.RUN_QUEUED,
            StreamEventTypes.RUN_IN_PROGRESS
        ]

    @staticmethod
    def get_completion_events() -> List[str]:
        """Get list of completion event types"""
        return [
            StreamEventTypes.RUN_COMPLETED,
            StreamEventTypes.MESSAGE_COMPLETED
        ]

    @staticmethod
    def get_error_events() -> List[str]:
        """Get list of error event types"""
        return [
            StreamEventTypes.RUN_FAILED,
            StreamEventTypes.RUN_CANCELLED
        ]