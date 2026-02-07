import time

from src.api.database.connection import engine, Base
# Import models so Base.metadata registers them
from src.api.models.user import User  # noqa: F401
from src.api.models.prediction_history import PredictionHistory  # noqa: F401


def create_tables(retries: int = 5, delay: float = 2.0):
    """Create all tables, retrying if the database is not yet ready."""
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables created successfully")
            return
        except Exception as e:
            if attempt < retries - 1:
                print(f"Database not ready (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(delay)
            else:
                print(f"Failed to create tables after {retries} attempts: {e}")
                raise
