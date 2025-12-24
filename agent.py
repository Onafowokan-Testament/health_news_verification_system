from typing import List, Tuple

from langchain.tools import tool
from langchain_core.documents import Document

from logger import logger

# OpenAI removed — using Gemini client instead
from pubmed_search import PubMedSearcher
from vector_store import HealthKnowledgeBase

# Optional Gemini adapter
try:
    from gemini_client import GeminiClient
except Exception:
    GeminiClient = None


class HealthCheckAgent:
    """RAG agent for health misinformation detection."""

    def __init__(
        self,
        config,
        knowledge_base: HealthKnowledgeBase,
        pubmed_searcher: PubMedSearcher,
    ):
        """Initialize the agent."""
        self.config = config
        self.knowledge_base = knowledge_base
        self.pubmed_searcher = pubmed_searcher
        # Create tools
        self.tools = self._create_tools()

        # Initialize Gemini client (Gemini is the sole provider)
        if GeminiClient is None:
            raise RuntimeError(
                "Gemini client not available. Install `google-genai` (pip install google-genai) and ensure it's importable."
            )
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY must be set in environment to use Gemini provider."
            )

        self.gemini_client = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_MODEL)
        self.model = None
        self.agent = None

    def _create_tools(self):
        """Create retrieval tools for the agent."""

        @tool(response_format="content_and_artifact")
        def search_curated_health_myths(query: str) -> Tuple[str, List[Document]]:
            """
            Search the curated database of Nigerian health myths and misconceptions.
            Use this FIRST before searching external sources.

            Args:
                query: The health claim or question to search for

            Returns:
                Formatted search results and raw documents
            """
            results = self.knowledge_base.search(query, k=self.config.TOP_K_RESULTS)

            if not results:
                return "No matching health myths found in curated database.", []

            # Format results
            formatted = []
            for i, doc in enumerate(results, 1):
                formatted.append(f"--- Curated Knowledge Result {i} ---")
                formatted.append(doc.page_content)
                formatted.append(f"Metadata: {doc.metadata}")
                formatted.append("")

            serialized = "\n".join(formatted)
            return serialized, results

        @tool(response_format="content_and_artifact")
        def search_pubmed_research(query: str) -> Tuple[str, List[Document]]:
            """
            Search PubMed for peer-reviewed medical research papers.
            Use this when curated database doesn't have sufficient information.

            Args:
                query: Medical research query

            Returns:
                Formatted PubMed results and raw documents
            """
            results = self.pubmed_searcher.search(
                query, max_results=self.config.PUBMED_MAX_RESULTS
            )

            if not results:
                return "No PubMed results found for this query.", []

            # Format results
            formatted = []
            for i, paper in enumerate(results, 1):
                formatted.append(f"--- PubMed Result {i} ---")
                formatted.append(f"Title: {paper['title']}")
                formatted.append(f"Authors: {paper['authors']}")
                formatted.append(f"Journal: {paper['journal']} ({paper['year']})")
                formatted.append(f"PMID: {paper['pmid']}")
                formatted.append(f"URL: {paper['url']}")
                formatted.append(f"Abstract: {paper['abstract']}")
                formatted.append("")

            serialized = "\n".join(formatted)

            # Convert to Document objects
            docs = [
                Document(
                    page_content=f"{p['title']}\n\n{p['abstract']}",
                    metadata={
                        "pmid": p["pmid"],
                        "journal": p["journal"],
                        "year": p["year"],
                        "url": p["url"],
                    },
                )
                for p in results
            ]

            return serialized, docs

        return [search_curated_health_myths, search_pubmed_research]

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are a health misinformation detection system designed for older adults in Nigeria.

Your job is to evaluate health claims and provide clear, accurate, compassionate information.

SEARCH STRATEGY:
1. ALWAYS search the curated health myths database FIRST using search_curated_health_myths
2. If the curated database has a good match (>75% relevant), use that information
3. If NOT found or you need more scientific evidence, search PubMed using search_pubmed_research
4. For complex claims, you may search both sources to provide comprehensive answers

RESPONSE FORMAT - YOU MUST ALWAYS PROVIDE:

**Verdict:** [TRUE / FALSE / PARTIALLY TRUE / UNCLEAR]

**Confidence:** [0-100%]
- 90-100%: Very confident, strong evidence
- 70-89%: Confident, good evidence
- 50-69%: Moderate confidence, some uncertainty
- Below 50%: Low confidence, unclear or conflicting evidence

**Explanation:**
[Provide a clear, simple explanation that an older adult can understand. Use everyday language, avoid medical jargon. If you must use medical terms, explain them simply.]

**Why This Matters:**
[Explain the real-world consequences - what could happen if someone believes this myth]

**What You Should Do Instead:**
[Provide practical, actionable advice]

**Trusted Sources:**
- [Source 1 with specific citation]
- [Source 2 with specific citation]
- [Source 3 if available]

IMPORTANT GUIDELINES:
- Be compassionate and respectful. Many people believe these myths because they were told by trusted family or community members.
- Never shame or mock people for believing myths
- Acknowledge cultural beliefs while gently correcting dangerous misinformation
- If a traditional practice is harmless but ineffective, acknowledge it while explaining what actually works
- For serious conditions (HIV, malaria, typhoid), be very clear about the need for medical treatment
- Always cite specific, authoritative sources (WHO, NCDC, peer-reviewed journals)
- If you're uncertain, say so. Don't guess about medical facts.
- For emergency situations (chest pain, severe bleeding, difficulty breathing), immediately advise seeking emergency medical care

SPECIAL CONSIDERATIONS FOR NIGERIAN CONTEXT:
- Reference Nigerian health authorities (NCDC, Federal Ministry of Health, NACA)
- Consider traditional practices that are harmless vs. those that are dangerous
- Be aware of common Nigerian health challenges (malaria, typhoid, hypertension)
- Respect local context while prioritizing evidence-based medicine
"""

    def check_claim(self, claim: str) -> dict:
        """
        Check a health claim and return structured response.

        Args:
            claim: The health claim to verify

        Returns:
            Dictionary with verdict, confidence, explanation, and sources
        """
        messages = []

        logger.info("Checking claim: %s", claim)

        # For Gemini-only flow, call Gemini API and include retrieval tool outputs in prompt
        # Get curated DB results and PubMed (if any)
        try:
            curated_serialized, curated_docs = self.tools[0](claim)
            logger.info("Curated DB returned %d results", len(curated_docs))
        except Exception:
            curated_serialized = "No matching health myths found in curated database."

        try:
            pubmed_serialized, pubmed_docs = self.tools[1](claim)
            logger.info("PubMed returned %d results", len(pubmed_docs))
        except Exception:
            pubmed_serialized = "No PubMed results found for this query."

        # Build user content with context
        context = """
CURATED_KNOWLEDGE:
{cur}

PUBMED_RESULTS:
{pub}
""".format(
            cur=curated_serialized, pub=pubmed_serialized
        )

        user_content = f"{claim}\n\nContext:\n{context}"

        # Call Gemini
        try:
            system_prompt = self._get_system_prompt()
            response_text = self.gemini_client.chat(system_prompt, user_content)
            logger.info(
                "Gemini returned response of length %d",
                len(response_text) if isinstance(response_text, str) else 0,
            )
        except Exception as e:
            logger.exception("Error calling Gemini: %s", e)
            response_text = f"Error calling Gemini: {e}"

        return {"claim": claim, "response": response_text, "messages": []}
