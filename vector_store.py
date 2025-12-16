from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from typing import List
import os

class HealthKnowledgeBase:
    """Manages the vector store for health myths."""
    
    def __init__(self, config):
        """Initialize vector store."""
        self.config = config
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        
        # Create data directory if it doesn't exist
        os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)
        
        # Initialize Chroma vector store
        self.vector_store = Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=config.VECTOR_DB_PATH
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
                    "claim": myth['claim'],
                    "verdict": myth['verdict'],
                    "confidence": myth['confidence'],
                    "category": myth['category'],
                    "language": myth.get('language', 'en')
                }
            )
            docs.append(doc)
        
        # Add documents to vector store
        self.vector_store.add_documents(docs)
        print(f"✓ Indexed {len(docs)} health myths into vector store")
    
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
