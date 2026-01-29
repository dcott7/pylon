"""
Database manager for Pylon game simulations.

Handles database connections, schema initialization, and data persistence.
Supports SQLite (development) and PostgreSQL (production).
"""

import logging
from typing import Any, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .schema import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and persistence for Pylon simulations.

    Supports both SQLite (for development/testing) and PostgreSQL (for production).
    Provides session management and convenience methods for inserting dimension
    and fact data.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        echo: bool = False,
    ) -> None:
        """
        Initialize the DatabaseManager.

        Args:
            connection_string: SQLAlchemy connection string. If None, defaults to
                an in-memory SQLite database for testing.
            echo: If True, log all SQL statements.
        """
        if connection_string is None:
            # In-memory SQLite for testing
            connection_string = "sqlite:///:memory:"
            logger.info("No connection string provided. Using in-memory SQLite.")

        self.connection_string = connection_string
        self.engine: Engine = self._create_engine(echo)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def _create_engine(self, echo: bool) -> Engine:
        """
        Create a SQLAlchemy engine with appropriate pool settings.

        SQLite in-memory databases need StaticPool to work with SQLAlchemy
        sessions. File-based and PostgreSQL use default pool settings.

        Args:
            echo: If True, log all SQL statements.

        Returns:
            Configured SQLAlchemy Engine.
        """
        if self.connection_string.startswith("sqlite:///:memory:"):
            return create_engine(
                self.connection_string,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo,
            )
        else:
            return create_engine(self.connection_string, echo=echo)

    def init_db(self) -> None:
        """
        Create all tables in the database.

        Idempotent: safe to call multiple times. Only creates missing tables.
        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.

        Caller is responsible for closing or using as context manager.

        Returns:
            A SQLAlchemy Session.
        """
        return self.SessionLocal()

    def insert_objects(self, *objects: Any, label: str = "object") -> None:
        """
        Generic insert for any ORM objects (dimension, fact, model invocation, etc.).

        Args:
            *objects: ORM objects to insert.
            label: Description for logging (e.g., "dimension", "fact", "model invocation").

        Raises:
            Exception: If insertion fails.
        """
        if not objects:
            logger.debug(f"No {label}(s) to insert.")
            return

        session = self.get_session()
        try:
            session.add_all(objects)
            session.commit()
            logger.info(f"Inserted {len(objects)} {label}(s).")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert {label}(s): {e}")
            raise
        finally:
            session.close()

    def insert_dimension_data(
        self,
        *objects: Any,
    ) -> None:
        """
        Insert dimension data (teams, athletes, formations, etc.).

        Args:
            *objects: ORM objects to insert (Team, Athlete, Formation, etc.)

        Raises:
            Exception: If insertion fails.
        """
        self.insert_objects(*objects, label="dimension")

    def insert_fact_data(
        self,
        *objects: Any,
    ) -> None:
        """
        Insert fact data (games, drives, plays, etc.).

        Args:
            *objects: ORM fact objects to insert (Game, Drive, Play, etc.)

        Raises:
            Exception: If insertion fails.
        """
        self.insert_objects(*objects, label="fact")

    def insert_model_invocations(
        self,
        *invocations: Any,
    ) -> None:
        """
        Insert model invocation records.

        Useful for post-game persistence of all model calls from a simulation.

        Args:
            *invocations: ModelInvocation objects to insert.

        Raises:
            Exception: If insertion fails.
        """
        self.insert_objects(*invocations, label="model invocation")

    def insert_dimension_data_or_ignore(
        self,
        *objects: Any,
    ) -> None:
        """
        Insert dimension data, ignoring/skipping duplicates (based on primary key or unique constraints).

        Useful for idempotent dimension data insertion where duplicates may exist.
        Uses merge() to handle both inserts and updates gracefully.

        Args:
            *objects: ORM objects to insert (Team, Athlete, Formation, etc.)
        """
        session = self.get_session()
        try:
            for obj in objects:
                # Merge handles both inserts and updates, skipping errors for duplicates
                try:
                    session.merge(obj)
                except Exception as obj_err:
                    logger.debug(f"Skipping duplicate object: {obj_err}")
                    session.rollback()
                    continue
            session.commit()
            logger.debug(f"Inserted/merged {len(objects)} dimension object(s).")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert dimension data: {e}")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close all connections in the pool."""
        self.engine.dispose()
        logger.info("Database connections closed.")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit. Closes database connection."""
        self.close()
