"""
Database utilities for Cloud Run optimized access.
Implements lazy loading and connection pooling.
"""
import logging
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager with lazy initialization for Cloud Run.
    Optimized for cold starts and stateless execution.
    """

    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init_engine(self, database_url: str, pool_size: int = 5):
        """
        Initialize database engine with connection pooling.

        For Cloud Run, we use a smaller pool size to avoid
        connection exhaustion during scaling.
        """
        if self._engine is None:
            logger.info("Initializing database engine")

            # Use QueuePool with conservative settings for Cloud Run
            self._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=2,
                pool_timeout=30,
                pool_recycle=1800,  # Recycle connections after 30 minutes
                pool_pre_ping=True,  # Verify connections before use
                echo=False
            )

            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )

            logger.info("Database engine initialized successfully")

    @property
    def engine(self):
        """Get database engine (lazy initialization)"""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized. Call init_engine() first.")
        return self._engine

    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def read_table(self, table_name: str) -> pd.DataFrame:
        """
        Read entire table into DataFrame.

        Args:
            table_name: Name of the table to read

        Returns:
            DataFrame with table contents
        """
        try:
            # Lazy initialization - try to initialize if not already done
            if self._engine is None:
                from app.config import Config
                database_url = Config.get_database_url()
                if database_url and database_url != "postgresql://postgres:@localhost:5432/reports_db":
                    self.init_engine(database_url)
                else:
                    logger.warning("Database not configured. Returning empty DataFrame.")
                    return pd.DataFrame()
            
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, self.engine)
            logger.info(f"Successfully read {len(df)} rows from {table_name}")
            return df
        except Exception as e:
            logger.error(f"Error reading table {table_name}: {e}")
            return pd.DataFrame()

    def write_table(self, df: pd.DataFrame, table_name: str, if_exists: str = 'replace'):
        """
        Write DataFrame to database table.

        Args:
            df: DataFrame to write
            table_name: Target table name
            if_exists: What to do if table exists ('replace', 'append', 'fail')
        """
        if df.empty:
            logger.warning(f"DataFrame for {table_name} is empty, skipping write")
            return

        try:
            with self.engine.connect() as conn:
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                logger.info(f"Successfully wrote {len(df)} rows to {table_name}")
        except Exception as e:
            logger.error(f"Error writing to table {table_name}: {e}")
            raise

    def truncate_table(self, table_name: str):
        """Truncate a table"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY"))
                conn.commit()
                logger.info(f"Truncated table {table_name}")
        except Exception as e:
            logger.error(f"Error truncating table {table_name}: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = :table_name)"
                ), {"table_name": table_name})
                return result.scalar()
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False

    def dispose(self):
        """Dispose of database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")


# Global database manager instance
db_manager = DatabaseManager()
