"""
Unit tests for the reCAPTCHA utility module.

These tests focus on the reCAPTCHA verification logic, error handling,
and the FastAPI dependency functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from fastapi import HTTPException, Request, Header

from Backend.utils.recaptcha import _verify_recaptcha, require_recaptcha
from Backend.config import settings

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestVerifyRecaptcha:
    """Test the _verify_recaptcha function."""

    @pytest.fixture
    def mock_recaptcha_payload(self):
        """Default reCAPTCHA verification payload."""
        return {
            "secret": "test_secret_key",
            "response": "test_token",
        }

    @pytest.fixture
    def mock_recaptcha_payload_with_ip(self):
        """reCAPTCHA verification payload with remote IP."""
        return {
            "secret": "test_secret_key",
            "response": "test_token",
            "remoteip": "192.168.1.1"
        }

    @pytest.fixture
    def mock_successful_response(self):
        """Mock successful reCAPTCHA response."""
        return {
            "success": True,
            "score": 0.8,
            "action": "test_action",
            "challenge_ts": "2024-01-01T12:00:00Z",
            "hostname": "localhost"
        }

    @pytest.fixture
    def mock_failed_response(self):
        """Mock failed reCAPTCHA response."""
        return {
            "success": False,
            "score": 0.1,
            "error-codes": ["invalid-input-response"]
        }

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha.aiohttp.ClientSession')
    async def test_verify_recaptcha_success_without_ip(
        self, mock_session_class, mock_settings, mock_successful_response
    ):
        """Test successful verification without remote IP."""
        # Setup
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

        # Create mock session and response using MagicMock for simpler async handling
        mock_session = MagicMock()
        mock_response = MagicMock()

        # Setup response
        mock_response.json = AsyncMock(return_value=mock_successful_response)

        # Setup session post to return the response in async context
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)

        # Setup session class to return session in async context
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await _verify_recaptcha("test_token", None)

        # Verify
        assert result == mock_successful_response
        mock_session.post.assert_called_once_with(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": "test_secret_key", "response": "test_token"}
        )

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha.aiohttp.ClientSession')
    async def test_verify_recaptcha_success_with_ip(
        self, mock_session_class, mock_settings, mock_successful_response
    ):
        """Test successful verification with remote IP."""
        # Setup
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

        # Create mock session and response using MagicMock for simpler async handling
        mock_session = MagicMock()
        mock_response = MagicMock()

        # Setup response
        mock_response.json = AsyncMock(return_value=mock_successful_response)

        # Setup session post to return the response in async context
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)

        # Setup session class to return session in async context
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await _verify_recaptcha("test_token", "192.168.1.1")

        # Verify
        assert result == mock_successful_response
        mock_session.post.assert_called_once_with(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": "test_secret_key",
                "response": "test_token",
                "remoteip": "192.168.1.1"
            }
        )

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha.aiohttp.ClientSession')
    async def test_verify_recaptcha_network_error(self, mock_session_class, mock_settings):
        """Test network error handling."""
        # Setup
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

        mock_session = MagicMock()
        mock_session.post.side_effect = aiohttp.ClientError("Network error")

        # Setup session class to return session in async context
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await _verify_recaptcha("test_token", None)

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "Failed to verify reCAPTCHA"

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha.aiohttp.ClientSession')
    async def test_verify_recaptcha_timeout_error(self, mock_session_class, mock_settings):
        """Test timeout error handling."""
        # Setup
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

        mock_session = MagicMock()
        mock_session.post.side_effect = aiohttp.ServerTimeoutError("Timeout")

        # Setup session class to return session in async context
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await _verify_recaptcha("test_token", None)

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "Failed to verify reCAPTCHA"


class TestRequireRecaptcha:
    """Test the require_recaptcha dependency function."""

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object."""
        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.1"
        return request

    @pytest.fixture
    def mock_request_no_client(self):
        """Mock FastAPI request object without client."""
        request = MagicMock(spec=Request)
        request.client = None
        return request

    @patch('Backend.utils.recaptcha.settings')
    async def test_bypass_when_testing(self, mock_settings, mock_request):
        """Test bypass when TESTING is True."""
        # Setup
        mock_settings.TESTING = True
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"

        dependency = require_recaptcha("test_action")

        # Execute
        result = await dependency(mock_request, "test_token", "test_action")

        # Verify
        assert result is None

    @patch('Backend.utils.recaptcha.settings')
    async def test_bypass_when_no_secret_key(self, mock_settings, mock_request):
        """Test bypass when no secret key is configured."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = ""

        dependency = require_recaptcha("test_action")

        # Execute
        result = await dependency(mock_request, "test_token", "test_action")

        # Verify
        assert result is None

    @patch('Backend.utils.recaptcha.settings')
    async def test_missing_token_error(self, mock_settings, mock_request):
        """Test error when token is missing."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"

        dependency = require_recaptcha("test_action")

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, None, "test_action")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Missing reCAPTCHA token"

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_verification_failure(self, mock_verify, mock_settings, mock_request):
        """Test error when reCAPTCHA verification fails."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_verify.return_value = {
            "success": False,
            "score": 0.1,
            "error-codes": ["invalid-input-response"]
        }

        dependency = require_recaptcha("test_action")

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, "test_token", "test_action")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "reCAPTCHA verification failed"

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_action_mismatch_error(self, mock_verify, mock_settings, mock_request):
        """Test error when action doesn't match expected."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_verify.return_value = {
            "success": True,
            "score": 0.8,
            "action": "wrong_action"
        }

        dependency = require_recaptcha("test_action")

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, "test_token", "test_action")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "reCAPTCHA action mismatch"

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_low_score_error(self, mock_verify, mock_settings, mock_request):
        """Test error when score is too low."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_MIN_SCORE = 0.5
        mock_verify.return_value = {
            "success": True,
            "score": 0.3,
            "action": "test_action"
        }

        dependency = require_recaptcha("test_action")

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, "test_token", "test_action")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "reCAPTCHA score too low"

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_successful_verification(self, mock_verify, mock_settings, mock_request):
        """Test successful reCAPTCHA verification."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_MIN_SCORE = 0.5
        mock_verify.return_value = {
            "success": True,
            "score": 0.8,
            "action": "test_action"
        }

        dependency = require_recaptcha("test_action")

        # Execute
        result = await dependency(mock_request, "test_token", "test_action")

        # Verify
        assert result is None
        mock_verify.assert_called_once_with("test_token", "192.168.1.1")

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_successful_verification_no_client(self, mock_verify, mock_settings, mock_request_no_client):
        """Test successful verification when request has no client."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_MIN_SCORE = 0.5
        mock_verify.return_value = {
            "success": True,
            "score": 0.8,
            "action": "test_action"
        }

        dependency = require_recaptcha("test_action")

        # Execute
        result = await dependency(mock_request_no_client, "test_token", "test_action")

        # Verify
        assert result is None
        mock_verify.assert_called_once_with("test_token", None)

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_successful_verification_no_action_header(self, mock_verify, mock_settings, mock_request):
        """Test successful verification without action header."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_MIN_SCORE = 0.5
        mock_verify.return_value = {
            "success": True,
            "score": 0.8,
            "action": None
        }

        dependency = require_recaptcha("test_action")

        # Execute
        result = await dependency(mock_request, "test_token", None)

        # Verify
        assert result is None
        mock_verify.assert_called_once_with("test_token", "192.168.1.1")

    @patch('Backend.utils.recaptcha.settings')
    @patch('Backend.utils.recaptcha._verify_recaptcha')
    async def test_successful_verification_no_expected_action(self, mock_verify, mock_settings, mock_request):
        """Test successful verification when no expected action is set."""
        # Setup
        mock_settings.TESTING = False
        mock_settings.RECAPTCHA_SECRET_KEY = "test_secret_key"
        mock_settings.RECAPTCHA_MIN_SCORE = 0.5
        mock_verify.return_value = {
            "success": True,
            "score": 0.8,
            "action": "some_action"
        }

        dependency = require_recaptcha("")  # Empty expected action

        # Execute
        result = await dependency(mock_request, "test_token", "some_action")

        # Verify
        assert result is None
        mock_verify.assert_called_once_with("test_token", "192.168.1.1")