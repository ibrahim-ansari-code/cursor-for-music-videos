"""
Unit tests for SSE formatting utilities
"""
import json
import re

from Backend.llm.brikli_agent.formatters import SSEFormatter, EventFilter
from Backend.llm.brikli_agent.constants import SSEMessageTypes, StreamEventTypes


class TestSSEFormatter:
    """Test cases for SSEFormatter class"""

    @staticmethod
    def _parse_sse_message(sse_message: str) -> dict:
        """
        Helper method to robustly parse SSE message content
        
        Args:
            sse_message: SSE formatted string
            
        Returns:
            Parsed JSON content as dictionary
        """
        # Use regex to extract JSON data from SSE format
        match = re.match(r'^data: (.+)\n\n$', sse_message)
        if not match:
            raise ValueError(f"Invalid SSE format: {sse_message}")
        
        json_data = match.group(1)
        return json.loads(json_data)

    def test_format_content(self):
        """Test formatting content as SSE message"""
        # Arrange
        content = "Hello, this is a test message"

        # Act
        result = SSEFormatter.format_content(content)

        # Assert
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON data using robust parsing
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.CONTENT
        assert parsed["content"] == content

    def test_format_status(self):
        """Test formatting status update as SSE message"""
        # Arrange
        status = "in_progress"

        # Act
        result = SSEFormatter.format_status(status)

        # Assert
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON data
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.STATUS
        assert parsed["status"] == status


    def test_format_done(self):
        """Test formatting completion message as SSE"""
        # Arrange
        total_content = "Here is the complete response from the assistant."

        # Act
        result = SSEFormatter.format_done(total_content)

        # Assert
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON data
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.DONE
        assert parsed["total_content"] == total_content

    def test_format_error(self):
        """Test formatting error message as SSE"""
        # Arrange
        error_message = "An error occurred while processing your request"

        # Act
        result = SSEFormatter.format_error(error_message)

        # Assert
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON data
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.ERROR
        assert parsed["error"] == error_message

    def test_format_empty_content(self):
        """Test formatting empty content"""
        # Act
        result = SSEFormatter.format_content("")

        # Assert
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.CONTENT
        assert parsed["content"] == ""

    def test_format_content_with_special_characters(self):
        """Test formatting content with special characters"""
        # Arrange
        content = 'Hello "world"! This has\nnewlines\tand\ttabs.'

        # Act
        result = SSEFormatter.format_content(content)

        # Assert
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.CONTENT
        assert parsed["content"] == content

    def test_format_content_with_unicode(self):
        """Test formatting content with unicode characters"""
        # Arrange
        content = "Hello 世界! Testing émojis 🎉 and ñoñe characters"

        # Act
        result = SSEFormatter.format_content(content)

        # Assert
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.CONTENT
        assert parsed["content"] == content

    def test_format_large_content(self):
        """Test formatting large content"""
        # Arrange
        content = "A" * 10000  # Large string

        # Act
        result = SSEFormatter.format_content(content)

        # Assert
        parsed = self._parse_sse_message(result)

        assert parsed["type"] == SSEMessageTypes.CONTENT
        assert parsed["content"] == content
        assert len(parsed["content"]) == 10000

    def test_sse_format_structure(self):
        """Test that all SSE messages follow correct structure"""
        # Test different message types
        methods_and_content = [
            (SSEFormatter.format_content, "test"),
            (SSEFormatter.format_status, "running"),
            (SSEFormatter.format_done, "complete"),
            (SSEFormatter.format_error, "error occurred")
        ]

        for method, content in methods_and_content:
            result = method(content)

            # All SSE messages should start with "data: " and end with "\n\n"
            assert result.startswith("data: ")
            assert result.endswith("\n\n")

            # Should contain valid JSON
            parsed = self._parse_sse_message(result)  # Should not raise exception

            # Should have a type field
            assert "type" in parsed
            assert isinstance(parsed["type"], str)


class TestEventFilter:
    """Test cases for EventFilter class"""

    def test_get_status_events(self):
        """Test getting status event types"""
        # Act
        status_events = EventFilter.get_status_events()

        # Assert
        assert isinstance(status_events, list)
        assert len(status_events) > 0

        # Check specific expected events
        expected_events = [
            StreamEventTypes.RUN_CREATED,
            StreamEventTypes.RUN_QUEUED,
            StreamEventTypes.RUN_IN_PROGRESS
        ]

        for event in expected_events:
            assert event in status_events

    def test_get_completion_events(self):
        """Test getting completion event types"""
        # Act
        completion_events = EventFilter.get_completion_events()

        # Assert
        assert isinstance(completion_events, list)
        assert len(completion_events) > 0

        # Check specific expected events
        expected_events = [
            StreamEventTypes.RUN_COMPLETED,
            StreamEventTypes.MESSAGE_COMPLETED
        ]

        for event in expected_events:
            assert event in completion_events

    def test_get_error_events(self):
        """Test getting error event types"""
        # Act
        error_events = EventFilter.get_error_events()

        # Assert
        assert isinstance(error_events, list)
        assert len(error_events) > 0

        # Check specific expected events
        expected_events = [
            StreamEventTypes.RUN_FAILED,
            StreamEventTypes.RUN_CANCELLED
        ]

        for event in expected_events:
            assert event in error_events

    def test_event_categories_are_distinct(self):
        """Test that event categories don't overlap"""
        # Act
        status_events = set(EventFilter.get_status_events())
        completion_events = set(EventFilter.get_completion_events())
        error_events = set(EventFilter.get_error_events())

        # Assert
        # No overlap between status and completion
        assert not status_events.intersection(completion_events)

        # No overlap between status and error
        assert not status_events.intersection(error_events)

        # No overlap between completion and error
        assert not completion_events.intersection(error_events)

    def test_all_event_lists_contain_strings(self):
        """Test that all event type lists contain only strings"""
        event_lists = [
            EventFilter.get_status_events(),
            EventFilter.get_completion_events(),
            EventFilter.get_error_events()
        ]

        for event_list in event_lists:
            for event in event_list:
                assert isinstance(event, str)
                assert len(event) > 0  # Non-empty string

    def test_event_filter_consistency(self):
        """Test that event filter methods are consistent"""
        # All methods should return lists
        assert isinstance(EventFilter.get_status_events(), list)
        assert isinstance(EventFilter.get_completion_events(), list)
        assert isinstance(EventFilter.get_error_events(), list)

        # All methods should return non-empty lists
        assert len(EventFilter.get_status_events()) > 0
        assert len(EventFilter.get_completion_events()) > 0
        assert len(EventFilter.get_error_events()) > 0

    def test_event_filter_returns_same_results(self):
        """Test that event filter methods return consistent results"""
        # Multiple calls should return the same results
        status_1 = EventFilter.get_status_events()
        status_2 = EventFilter.get_status_events()
        assert status_1 == status_2

        completion_1 = EventFilter.get_completion_events()
        completion_2 = EventFilter.get_completion_events()
        assert completion_1 == completion_2

        error_1 = EventFilter.get_error_events()
        error_2 = EventFilter.get_error_events()
        assert error_1 == error_2