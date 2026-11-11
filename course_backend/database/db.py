import os
import sqlite3
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import event

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("PRAKTIKA_DB", str(ROOT / "data" / "praktika.sqlite3")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")


def init_db() -> None:
    """Create the project's authoritative tables before ORM initialization."""
    if DATABASE_URL.startswith("sqlite"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
            with sqlite3.connect(DB_PATH) as connection:
                connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
