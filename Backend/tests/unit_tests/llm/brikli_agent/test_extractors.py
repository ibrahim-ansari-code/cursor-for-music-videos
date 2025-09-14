"""
Unit tests for event data extraction utilities
"""
import pytest
from unittest.mock import Mock, PropertyMock

from Backend.llm.brikli_agent.extractors import EventExtractor


class TestEventExtractor:
    """Test cases for EventExtractor class"""

    def test_extract_message_delta_with_text_value(self):
        """Test extracting message delta with text.value structure"""
        # Arrange
        text_obj = Mock()
        text_obj.value = "Hello world!"

        content_part = Mock()
        content_part.text = text_obj

        delta = Mock()
        delta.content = [content_part]

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Hello world!"

    def test_extract_message_delta_with_direct_text_string(self):
        """Test extracting message delta with direct text string"""
        # Arrange
        content_part = Mock()
        content_part.text = "Direct string content"

        delta = Mock()
        delta.content = [content_part]

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Direct string content"

    def test_extract_message_delta_with_direct_content_text(self):
        """Test extracting message delta with direct content.text structure"""
        # Arrange
        text_obj = Mock()
        text_obj.value = "Content text value"

        delta = Mock()
        delta.content = Mock()
        delta.content.text = text_obj

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Content text value"

    def test_extract_message_delta_with_direct_content_string(self):
        """Test extracting message delta with direct content.text as string"""
        # Arrange
        delta = Mock()
        delta.content = Mock()
        delta.content.text = "Direct content string"

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Direct content string"

    def test_extract_message_delta_with_delta_text_value(self):
        """Test extracting message delta with delta.text.value structure"""
        # Arrange
        text_obj = Mock()
        text_obj.value = "Delta text content"

        delta = Mock()
        delta.text = text_obj
        # Ensure content check fails so it goes to delta.text path
        delta.content = None

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Delta text content"

    def test_extract_message_delta_with_delta_text_string(self):
        """Test extracting message delta with delta.text as string"""
        # Arrange
        delta = Mock()
        delta.text = "Delta text string"
        # Ensure content check fails so it goes to delta.text path
        delta.content = None

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Delta text string"

    def test_extract_message_delta_no_delta(self):
        """Test extracting message delta when no delta attribute"""
        # Arrange
        event_data = Mock()
        del event_data.delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_message_delta_empty_content(self):
        """Test extracting message delta with empty content"""
        # Arrange
        delta = Mock()
        delta.content = []
        # Ensure delta.text doesn't exist so it returns empty
        del delta.text

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_message_delta_empty_text_value(self):
        """Test extracting message delta with empty text value"""
        # Arrange
        text_obj = Mock()
        text_obj.value = ""

        content_part = Mock()
        content_part.text = text_obj

        delta = Mock()
        delta.content = [content_part]

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_message_delta_multiple_content_parts(self):
        """Test extracting message delta with multiple content parts"""
        # Arrange
        # First part has empty content
        empty_text = Mock()
        empty_text.value = ""
        empty_content = Mock()
        empty_content.text = empty_text

        # Second part has actual content
        valid_text = Mock()
        valid_text.value = "Valid content"
        valid_content = Mock()
        valid_content.text = valid_text

        delta = Mock()
        delta.content = [empty_content, valid_content]

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "Valid content"

    def test_extract_message_delta_exception_handling(self):
        """Test exception handling in message delta extraction"""
        # Arrange
        event_data = Mock()
        # Simulate an exception during content access
        delta = Mock()
        # Make content access raise an exception
        type(delta).content = PropertyMock(side_effect=Exception("Test error"))
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_message_creation_with_text_value(self):
        """Test extracting step delta for message creation with text.value"""
        # Arrange
        text_obj = Mock()
        text_obj.value = "Assistant response content"

        content_item = Mock()
        content_item.text = text_obj

        message = Mock()
        message.content = [content_item]

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == "Assistant response content"

    def test_extract_step_delta_message_creation_with_text_string(self):
        """Test extracting step delta for message creation with text string"""
        # Arrange
        content_item = Mock()
        content_item.text = "Direct text string"

        message = Mock()
        message.content = [content_item]

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == "Direct text string"

    def test_extract_step_delta_message_creation_direct_content(self):
        """Test extracting step delta with direct content.text structure"""
        # Arrange
        text_obj = Mock()
        text_obj.value = "Direct content text"

        message = Mock()
        message.content = Mock()
        message.content.text = text_obj

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == "Direct content text"

    def test_extract_step_delta_tool_calls_type(self):
        """Test extracting step delta for tool_calls type (should return empty)"""
        # Arrange
        step_details = Mock()
        step_details.type = "tool_calls"

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_unknown_type(self):
        """Test extracting step delta for unknown type"""
        # Arrange
        step_details = Mock()
        step_details.type = "unknown_type"

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_no_delta(self):
        """Test extracting step delta when no delta attribute"""
        # Arrange
        event_data = Mock()
        del event_data.delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_no_step_details(self):
        """Test extracting step delta when no step_details"""
        # Arrange
        delta = Mock()
        del delta.step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_no_message_creation(self):
        """Test extracting step delta when no message_creation"""
        # Arrange
        step_details = Mock()
        step_details.type = "message_creation"
        del step_details.message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_empty_content(self):
        """Test extracting step delta with empty content"""
        # Arrange
        message = Mock()
        message.content = []

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_step_delta_multiple_content_items(self):
        """Test extracting step delta with multiple content items"""
        # Arrange
        # First item has empty content
        empty_text = Mock()
        empty_text.value = ""
        empty_item = Mock()
        empty_item.text = empty_text

        # Second item has valid content
        valid_text = Mock()
        valid_text.value = "Valid step content"
        valid_item = Mock()
        valid_item.text = valid_text

        message = Mock()
        message.content = [empty_item, valid_item]

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == "Valid step content"

    def test_extract_step_delta_exception_handling(self):
        """Test exception handling in step delta extraction"""
        # Arrange
        event_data = Mock()
        # Simulate an exception
        event_data.delta = Mock()
        event_data.delta.step_details = Mock()
        event_data.delta.step_details.type = Mock(side_effect=Exception("Test error"))

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == ""

    def test_extract_message_delta_with_numeric_content(self):
        """Test extracting message delta converts numeric content to string"""
        # Arrange
        text_obj = Mock()
        text_obj.value = 12345

        content_part = Mock()
        content_part.text = text_obj

        delta = Mock()
        delta.content = [content_part]

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_message_delta(event_data)

        # Assert
        assert result == "12345"
        assert isinstance(result, str)

    def test_extract_step_delta_with_numeric_content(self):
        """Test extracting step delta converts numeric content to string"""
        # Arrange
        text_obj = Mock()
        text_obj.value = 67890

        content_item = Mock()
        content_item.text = text_obj

        message = Mock()
        message.content = [content_item]

        message_creation = Mock()
        message_creation.message = message

        step_details = Mock()
        step_details.type = "message_creation"
        step_details.message_creation = message_creation

        delta = Mock()
        delta.step_details = step_details

        event_data = Mock()
        event_data.delta = delta

        # Act
        result = EventExtractor.extract_step_delta(event_data)

        # Assert
        assert result == "67890"
        assert isinstance(result, str)