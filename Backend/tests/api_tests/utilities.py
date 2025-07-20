from fastapi.testclient import TestClient


class TestClientWithHost(TestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers.update({"Host": "localhost"})


from uuid import uuid4
from Backend.models.user import User
from Backend.models.enums import UserType

def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD", is_admin=False):
    """
    Creates a mock user for testing purposes.
    
    Args:
        user_id: UUID for the user, generates new one if None
        email: Email address for the user
        user_type: UserType enum value or string (LANDLORD, TENANT, ADMIN, STAFF)
        is_admin: Whether user has admin privileges
    """
    # Handle both UserType enum and string inputs safely
    if isinstance(user_type, UserType):
        resolved_user_type = user_type
    else:
        try:
            resolved_user_type = UserType[user_type]
        except KeyError:
            # Fallback to LANDLORD for invalid user_type strings
            resolved_user_type = UserType.LANDLORD
    
    return User(
        id=user_id or uuid4(),
        email=email,
        user_type=resolved_user_type,
        is_admin=is_admin,
    ) 