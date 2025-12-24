import os
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document

from logger import logger

# Optional Gemini embeddings adapter
try:
    from google import genai
except Exception:
    genai = None


class GeminiEmbeddings:
    """Minimal embeddings adapter using Google GenAI SDK."""

    def __init__(self, model: str = "gemini-text-embedding-1.0"):
        if genai is None:
            raise RuntimeError(
                "google-genai package not installed. Install with: pip install google-genai"
            )
        self.model = model
        # Initialize client
        try:
            self.client = genai.Client()
        except Exception:
            import os

            os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
            self.client = genai.Client()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Use the official embeddings API
        resp = self.client.embeddings.create(model=self.model, input=texts)
        embeddings = []
        for item in getattr(resp, "data", []) or []:
            vec = (
                item.get("embedding")
                if isinstance(item, dict)
                else getattr(item, "embedding", None)
            )
            if vec is None:
                raise RuntimeError("Unexpected embeddings response from Gemini client")
            embeddings.append(vec)
        return embeddings


class HealthKnowledgeBase:
    """Manages the vector store for health myths."""

    def __init__(self, config):
        """Initialize vector store."""
        self.config = config
        # Initialize embeddings using Gemini adapter (must be installed)
        logger.info("Initializing embeddings (Gemini): %s", config.EMBEDDING_MODEL)
        try:
            self.embeddings = GeminiEmbeddings(model=config.EMBEDDING_MODEL)
            logger.info("Embeddings initialized successfully")
        except Exception as e:
            logger.exception("Embedding initialization failed: %s", e)
            raise RuntimeError(f"Embedding initialization failed: {e}")

        # Create data directory if it doesn't exist
        os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)

        # Initialize Chroma vector store
        self.vector_store = Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=config.VECTOR_DB_PATH,
        )

    def index_myths(self, myths: List[dict]) -> None:
        """
        Index curated health myths into vector store.

        Args:
            myths: List of myth dictionaries
        """
        docs = []
        for myth in myths:
            content = f"""
Health Claim: {myth['claim']}
Verdict: {myth['verdict']}
Confidence: {myth['confidence']}%

Explanation: {myth['explanation']}

Trusted Sources:
{chr(10).join(f"- {source}" for source in myth['sources'])}

Category: {myth['category']}
            """.strip()

            doc = Document(
                page_content=content,
                metadata={
                    "claim": myth["claim"],
                    "verdict": myth["verdict"],
                    "confidence": myth["confidence"],
                    "category": myth["category"],
                    "language": myth.get("language", "en"),
                },
            )
            docs.append(doc)

        # Add documents to vector store
        self.vector_store.add_documents(docs)
        logger.info("Indexed %d health myths into vector store", len(docs))

    def search(self, query: str, k: int = 2) -> List[Document]:
        """
        Search vector store for relevant myths.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant documents
        """
        return self.vector_store.similarity_search(query, k=k)

    def get_count(self) -> int:
        """Get total number of indexed documents."""
        return self.vector_store._collection.count()
