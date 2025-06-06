# Import all models to ensure they are registered with SQLModel/SQLAlchemy
# before any relationship mapping or configuration occurs.
from . import user
from . import property
from . import tenant
from . import lease
from . import accounting
from . import maintenance
from . import reports
from . import enums

# Initialize models to resolve circular dependencies if needed


def initialize_models():
    """Configure mappers after all models are imported."""
    try:
        from sqlalchemy.orm import configure_mappers

        # Configure all mappers to resolve relationships defined within classes
        configure_mappers()
        print("SQLAlchemy mappers configured successfully.")
    except Exception as e:
        print(f"Error configuring SQLAlchemy mappers: {e}")
        # Optionally re-raise or handle the error
        raise


# Run the initialization function
initialize_models()
