import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Field, Session, SQLModel, create_engine

_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")


class ClaimCheckRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_label: str = Field(index=True, max_length=100)
    claim: str
    verdict: str = Field(index=True, max_length=30)
    response: str
    language: str = Field(max_length=30)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str = Field(max_length=255)
    display_name: str = Field(default="", max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AdminTruth(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    claim: str = Field(index=True)
    verdict: str = Field(default="TRUE", max_length=30)
    confidence: int = Field(default=90)
    explanation: str
    sources_text: str = Field(default="")
    category: str = Field(default="general", max_length=100)
    language: str = Field(default="en", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


def _normalize_database_url(url: str) -> str:
    """Force SQLAlchemy to use psycopg v3 (`psycopg` package).

    Bare ``postgresql://`` URLs default to the ``psycopg2`` dialect, which we do not
    install. Render and others supply Postgres URLs without a ``+driver`` suffix.
    """
    if not url or url.startswith("sqlite"):
        return url
    scheme_part = url.split("://", 1)[0]
    if "+" in scheme_part:
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


DB_PATH = "./data/app.db"
os.makedirs("./data", exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_URL = f"sqlite:///{DB_PATH}"
EFFECTIVE_DB_URL = _normalize_database_url(DATABASE_URL) if DATABASE_URL else SQLITE_URL

_connect_args: dict = {}
_engine_kwargs: dict = {"echo": False}

if EFFECTIVE_DB_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _engine_kwargs["connect_args"] = _connect_args
else:
    # Recover dropped connections (common with managed Postgres); optional SSL mode via env.
    _engine_kwargs["pool_pre_ping"] = True
    _ssl = os.getenv("DATABASE_SSLMODE", "").strip()
    if _ssl:
        _connect_args = {"sslmode": _ssl}
        _engine_kwargs["connect_args"] = _connect_args

engine = create_engine(EFFECTIVE_DB_URL, **_engine_kwargs)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
