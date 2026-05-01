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


DB_PATH = "./data/app.db"
os.makedirs("./data", exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_URL = f"sqlite:///{DB_PATH}"
EFFECTIVE_DB_URL = DATABASE_URL or SQLITE_URL

connect_args = {"check_same_thread": False} if EFFECTIVE_DB_URL.startswith("sqlite") else {}
engine = create_engine(EFFECTIVE_DB_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
