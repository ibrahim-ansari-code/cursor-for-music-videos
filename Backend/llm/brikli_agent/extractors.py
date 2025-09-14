"""
Event data extraction utilities for Azure AI streaming events
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventExtractor:
    """
    Handles extraction of content from Azure AI streaming event data

    This class provides methods to extract text content from different
    types of Azure AI streaming events, handling the various data
    structures that may be returned.
    """

    @staticmethod
    def extract_message_delta(event_data: Any) -> str:
        """
        Extract content from Azure AI Projects message delta event
        Handles direct message content deltas
        """
        try:
            if not hasattr(event_data, 'delta'):
                return ""

            delta = event_data.delta

            # Handle delta content list
            if hasattr(delta, 'content') and delta.content:
                if isinstance(delta.content, list):
                    for content_part in delta.content:
                        if hasattr(content_part, 'text'):
                            text_obj = content_part.text
                            if hasattr(text_obj, 'value'):
                                content = str(text_obj.value)
                                if content:
                                    return content
                            elif isinstance(text_obj, str):
                                if text_obj:
                                    return text_obj

                # Handle direct content object
                elif hasattr(delta.content, 'text'):
                    text_obj = delta.content.text
                    if hasattr(text_obj, 'value'):
                        content = str(text_obj.value)
                        if content:
                            return content
                    elif isinstance(text_obj, str):
                        if text_obj:
                            return text_obj

            # Handle delta text directly
            elif hasattr(delta, 'text'):
                text_obj = delta.text
                if hasattr(text_obj, 'value'):
                    content = str(text_obj.value)
                    if content:
                        return content
                elif isinstance(text_obj, str):
                    if text_obj:
                        return text_obj

            return ""

        except Exception as e:
            logger.error(f"Error extracting message delta: {e}")
            return ""

    @staticmethod
    def extract_step_delta(event_data: Any) -> str:
        """
        Extract content from Azure AI Projects step delta event
        Handles message_creation type step details for assistant responses
        """
        try:
            if not hasattr(event_data, 'delta'):
                return ""

            delta = event_data.delta

            # Check for step details
            if not hasattr(delta, 'step_details'):
                return ""

            step_details = delta.step_details
            step_type = getattr(step_details, 'type', None)

            # Only process message_creation type steps (not tool_calls)
            if step_type != 'message_creation':
                return ""

            # Extract message creation content
            if hasattr(step_details, 'message_creation'):
                message_creation = step_details.message_creation

                if hasattr(message_creation, 'message'):
                    message = message_creation.message

                    if hasattr(message, 'content') and message.content:
                        # Handle content list
                        if isinstance(message.content, list):
                            for content_item in message.content:
                                if hasattr(content_item, 'text'):
                                    text_obj = content_item.text
                                    if hasattr(text_obj, 'value'):
                                        content = str(text_obj.value)
                                        if content:
                                            return content
                                    elif isinstance(text_obj, str):
                                        if text_obj:
                                            return text_obj

                        # Handle direct content object
                        elif hasattr(message.content, 'text'):
                            text_obj = message.content.text
                            if hasattr(text_obj, 'value'):
                                content = str(text_obj.value)
                                if content:
                                    return content
                            elif isinstance(text_obj, str):
                                if text_obj:
                                    return text_obj

            return ""

        except Exception as e:
            logger.error(f"Error extracting step delta: {e}")
            return ""