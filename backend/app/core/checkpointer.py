from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_pool: Any = None
_checkpointer: Any = None


def _make_psycopg_conn_string() -> str:
    """Convert SQLAlchemy DATABASE_URL to a plain psycopg connection string."""
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5431/aitutordb")
    return (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg+psycopg://", "postgresql://")
    )


async def init_checkpointer() -> Any | None:
    """Open an async connection pool and initialise AsyncPostgresSaver.

    Returns the checkpointer on success, None on failure (server still starts
    but graphs run without persistence).
    """
    global _pool, _checkpointer
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        conn_str = _make_psycopg_conn_string()
        _pool = AsyncConnectionPool(conn_str, open=False, max_size=10)
        await _pool.open(wait=True)

        _checkpointer = AsyncPostgresSaver(_pool)
        # Creates the LangGraph checkpoint tables if they don't exist yet.
        await _checkpointer.setup()

        logger.info("LangGraph AsyncPostgresSaver checkpointer ready.")
        return _checkpointer

    except Exception as exc:
        logger.warning(
            "Could not initialise LangGraph Postgres checkpointer (%s). "
            "Graphs will run without persistence.",
            exc,
        )
        _pool = None
        _checkpointer = None
        return None


async def close_checkpointer() -> None:
    """Close the connection pool on server shutdown."""
    global _pool, _checkpointer
    if _pool is not None:
        try:
            await _pool.close()
            logger.info("LangGraph checkpointer connection pool closed.")
        except Exception as exc:
            logger.warning("Error closing checkpointer pool: %s", exc)
        _pool = None
        _checkpointer = None


def get_checkpointer() -> Any | None:
    return _checkpointer
