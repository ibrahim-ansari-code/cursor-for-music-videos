"""
Unit tests for the lease update service functions.
"""
import pytest
import logging
from unittest.mock import AsyncMock

from Backend.api.leases.service import update_lease, update_lease_status, validate_lease
from Backend.api.leases.schemas import LeaseUpdate
from Backend.models.user import User
from Backend.models.lease import Lease

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)

# TODO: Write unit tests for update_lease, update_lease_status, and validate_lease functions 