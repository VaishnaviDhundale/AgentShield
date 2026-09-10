"""
Database Engine and Session Management for AgentShield
"""

import os
from pathlib import Path
from typing import Generator, Optional
from sqlmodel import SQLModel, create_engine, Session


DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_URL = f"sqlite:///{DB_DIR / 'agentshield.db'}"

_engine = None


def get_engine(db_url: Optional[str] = None):
    global _engine
    if _engine is None or db_url is not None:
        url = db_url or os.environ.get("AGENTSHIELD_DB_URL", DEFAULT_DB_URL)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, echo=False, connect_args=connect_args)
        SQLModel.metadata.create_all(_engine)
    return _engine


def get_session(db_url: Optional[str] = None) -> Generator[Session, None, None]:
    engine = get_engine(db_url)
    with Session(engine) as session:
        yield session


def init_db(db_url: Optional[str] = None) -> None:
    """Initializes the database schema."""
    engine = get_engine(db_url)
    SQLModel.metadata.create_all(engine)
