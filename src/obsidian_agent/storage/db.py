"""Database bootstrap helpers."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from obsidian_agent.domain.models import Base


def create_session_factory(sqlite_path: Path) -> sessionmaker[Session]:
    """Create a SQLite session factory."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
