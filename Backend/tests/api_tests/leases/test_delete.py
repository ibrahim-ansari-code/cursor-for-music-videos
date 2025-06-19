"""
Unit tests for the lease deletion service functions.
"""
import pytest
import logging
from unittest.mock import AsyncMock

from Backend.api.leases.service import delete_lease
from Backend.models.user import User
from Backend.models.lease import Lease

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)

# TODO: Write unit tests for delete_lease function 