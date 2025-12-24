import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")

    # PubMed Configuration
    PUBMED_EMAIL: str = os.getenv("PUBMED_EMAIL", "your-email@example.com")
    PUBMED_MAX_RESULTS: int = 3

    # Model Configuration
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-text-embedding-1.0")
    TEMPERATURE: float = 0.1

    # Vector Store Configuration
    VECTOR_DB_PATH: str = "./data/chroma_db"
    COLLECTION_NAME: str = "nigerian_health_myths"

    # Search Configuration
    SIMILARITY_THRESHOLD: float = 0.75
    TOP_K_RESULTS: int = 2

    # UI Configuration
    APP_TITLE: str = "🏥 Nigerian Health Claim Checker"
    APP_ICON: str = "🏥"
    SUPPORTED_LANGUAGES: list = None

    # Gemini configuration (single provider)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def __post_init__(self):
        if self.SUPPORTED_LANGUAGES is None:
            self.SUPPORTED_LANGUAGES = ["English", "Pidgin", "Yoruba", "Hausa", "Igbo"]

        # Enable LangSmith tracing if API key provided
        if self.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = self.LANGSMITH_API_KEY

    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required. Set it in .env file.")
        if not self.PUBMED_EMAIL or self.PUBMED_EMAIL == "your-email@example.com":
            print("⚠️  Warning: Using default PUBMED_EMAIL. Set a real email in .env")
        return True
