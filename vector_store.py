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

    def __init__(self, model: str = "gemini-embedding-001"):
        if genai is None:
            raise RuntimeError(
                "google-genai package not installed. Install with: pip install google-genai"
            )
        self.model = model
        try:
            self.client = genai.Client()
        except Exception:
            os.environ.setdefault("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
            self.client = genai.Client()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch embed for indexing (retrieval document task)."""
        if not texts:
            return []
        all_vecs: List[List[float]] = []
        chunk_size = 100
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            resp = self.client.models.embed_content(
                model=self.model,
                contents=chunk,
                config={"task_type": "RETRIEVAL_DOCUMENT"},
            )
            embs = resp.embeddings or []
            if len(embs) != len(chunk):
                raise RuntimeError(
                    f"Embedding count mismatch: expected {len(chunk)}, got {len(embs)}"
                )
            for emb in embs:
                vals = getattr(emb, "values", None)
                if not vals:
                    raise RuntimeError("Unexpected embeddings response from Gemini client")
                all_vecs.append(list(vals))
        return all_vecs

    def embed_query(self, text: str) -> List[float]:
        """Single-query embedding for similarity search."""
        resp = self.client.models.embed_content(
            model=self.model,
            contents=[text],
            config={"task_type": "RETRIEVAL_QUERY"},
        )
        embs = resp.embeddings or []
        if len(embs) != 1:
            raise RuntimeError(f"Expected 1 query embedding, got {len(embs)}")
        vals = getattr(embs[0], "values", None)
        if not vals:
            raise RuntimeError("Unexpected query embedding from Gemini client")
        return list(vals)


class HealthKnowledgeBase:
    """Manages the vector store for health myths."""

    def __init__(self, config):
        """Initialize vector store."""
        self.config = config
        # Initialize embeddings using Gemini adapter (must be installed)
        logger.info("Initializing embeddings (Gemini): {}", config.EMBEDDING_MODEL)
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

    def rebuild_index(self, myths: List[dict]) -> None:
        """
        Rebuild the collection from scratch using provided myths.
        Useful after admin edits to keep retrieval in sync.
        """
        try:
            existing = self.vector_store.get()
            ids = existing.get("ids", []) if isinstance(existing, dict) else []
            if ids:
                self.vector_store.delete(ids=ids)
                logger.info("Deleted {} existing vector documents", len(ids))
        except Exception as e:
            logger.exception("Failed clearing vector collection: %s", e)
            raise RuntimeError(f"Failed to clear vector collection: {e}")

        self.index_myths(myths)

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
