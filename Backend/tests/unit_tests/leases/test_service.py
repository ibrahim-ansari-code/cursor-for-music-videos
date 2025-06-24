"""
Unit tests for miscellaneous lease service functions.
"""
import pytest
import logging
from unittest.mock import AsyncMock

from fastapi import UploadFile

from Backend.api.leases.service import (
    analyze_lease,
    parse_lease,
    upload_lease,
    upload_lease_document,
)
from Backend.models.user import User

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)

# TODO: Write unit tests for miscellaneous lease service functions 