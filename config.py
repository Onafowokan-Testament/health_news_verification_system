import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Names that appear in old docs / .env examples but are not valid for embedContent on the current API.
_LEGACY_EMBEDDING_ALIASES: dict[str, str] = {
    "gemini-text-embedding-1.0": "gemini-embedding-001",
    "gemini-text-embedding-004": "gemini-embedding-001",
    "text-embedding-004": "gemini-embedding-001",
}


@dataclass
class Config:
    """Application configuration."""

    # API Keys (default_factory so values are read when Config() runs, not at class definition time)
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    LANGSMITH_API_KEY: str = field(default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "").strip())

    # PubMed Configuration (Entrez): optional — omit email or set PUBMED_ENABLED=false to skip PubMed calls.
    PUBMED_EMAIL: str = field(default_factory=lambda: os.getenv("PUBMED_EMAIL", "").strip())
    PUBMED_API_KEY: str = field(default_factory=lambda: os.getenv("PUBMED_API_KEY", "").strip())
    PUBMED_TOOL: str = field(default_factory=lambda: os.getenv("PUBMED_TOOL", "MedVer").strip())
    # Default off so you can run MedVer without sharing an Entrez contact email.
    PUBMED_ENABLED: bool = field(
        default_factory=lambda: _env_bool("PUBMED_ENABLED", False)
    )
    PUBMED_MAX_RESULTS: int = 3

    # Model Configuration
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    )
    TEMPERATURE: float = 0.1

    # Vector Store Configuration
    VECTOR_DB_PATH: str = "./data/chroma_db"
    COLLECTION_NAME: str = "nigerian_health_myths"

    # Search Configuration
    SIMILARITY_THRESHOLD: float = 0.75
    TOP_K_RESULTS: int = 2

    # UI Configuration
    APP_TITLE: str = "🏥 MedVer"
    APP_ICON: str = "🏥"
    SUPPORTED_LANGUAGES: list = None

    def __post_init__(self):
        if self.SUPPORTED_LANGUAGES is None:
            self.SUPPORTED_LANGUAGES = ["English", "Pidgin", "Yoruba", "Hausa", "Igbo"]

        # Enable LangSmith tracing if API key provided
        if self.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = self.LANGSMITH_API_KEY

        emb = (self.EMBEDDING_MODEL or "").strip()
        alias_key = emb.lower()
        if alias_key in _LEGACY_EMBEDDING_ALIASES:
            replacement = _LEGACY_EMBEDDING_ALIASES[alias_key]
            print(
                f"⚠️  EMBEDDING_MODEL '{emb}' is not supported for embedContent — "
                f"using '{replacement}'. Update .env to silence this."
            )
            self.EMBEDDING_MODEL = replacement

        chat_model = (self.GEMINI_MODEL or "").strip()
        cm_norm = chat_model.lower().removeprefix("models/")
        if "embedding" in cm_norm or cm_norm.startswith("text-embedding"):
            print(
                f"⚠️  GEMINI_MODEL '{chat_model}' is not valid for chat (generate_content) — "
                f"using 'gemini-2.5-flash'. Set GEMINI_MODEL to a chat model in .env."
            )
            self.GEMINI_MODEL = "gemini-2.5-flash"

    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required. Set it in .env file.")

        if self.PUBMED_ENABLED and not self.PUBMED_EMAIL:
            print(
                "⚠️  PubMed is enabled but PUBMED_EMAIL is empty — disabling PubMed. "
                "Set PUBMED_EMAIL or turn PubMed off with PUBMED_ENABLED=false."
            )
            self.PUBMED_ENABLED = False

        if self.PUBMED_ENABLED:
            print("✓ PubMed (Entrez) enabled — curated retrieval plus PubMed search.")

        return True
