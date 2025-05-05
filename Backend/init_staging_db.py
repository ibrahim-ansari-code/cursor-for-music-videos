import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Initializes the staging database schema using SQLModel."""
    logger.info("Script started: Initializing staging database schema.")

    # --- Environment Loading ---
    dotenv_path = os.getenv("DOTENV_KEY")
    if not dotenv_path:
        logger.error("Error: DOTENV_KEY environment variable not set.")
        logger.info("Please set DOTENV_KEY to point to your staging .env file (e.g., .env.staging)")
        logger.info("Example (PowerShell): $env:DOTENV_KEY='.env.staging'; python scripts/init_staging_db.py")
        logger.info("Example (Bash): export DOTENV_KEY='.env.staging' && python scripts/init_staging_db.py")
        return

    if not os.path.exists(dotenv_path):
         logger.error(f"Error: Environment file not found at '{dotenv_path}'")
         return

    logger.info(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path, override=True) # Override system env vars if necessary

    # --- Dynamic Imports (After env load) ---
    # Ensure the script can find the Backend module.
    # Assumes the script is in 'scripts' and 'Backend' is one level up (project root).
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        logger.info(f"Added project root to sys.path: {project_root}")

    try:
        # Ensure models are loaded so SQLModel.metadata is populated BEFORE init_db is called
        logger.info("Importing Backend.models...")
        import Backend.models
        logger.info("Backend.models imported successfully.")

        logger.info("Importing database functions...")
        from Backend.database import init_db, get_database_url, engine # Import engine too for disposal
        logger.info("Database functions imported successfully.")

        # --- Database Initialization ---
        db_url = get_database_url()
        # Basic masking for logging - improves security slightly
        masked_db_url = db_url.split('@')[-1] if '@' in db_url else db_url
        logger.info(f"Targeting database host/db: ...@{masked_db_url}")

        logger.info("Calling init_db()...")
        await init_db()
        logger.info("Database initialization process completed successfully.")

    except ImportError as e:
        logger.error(f"Import error: {e}. Make sure you run this script from the project root directory.")
        logger.error("Ensure Backend modules are discoverable (check PYTHONPATH or run from root).")
    except Exception as e:
        logger.exception(f"An error occurred during database initialization: {e}")
    finally:
        # --- Cleanup ---
        # Dispose of the engine connection pool
        if 'engine' in locals() and engine:
            logger.info("Disposing database engine connection pool...")
            await engine.dispose()
            logger.info("Engine disposed.")


if __name__ == "__main__":
    asyncio.run(main()) 