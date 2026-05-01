# Copilot Instructions for Nigerian Health News Verification System

This RAG (Retrieval-Augmented Generation) system helps older adults verify health claims using curated medical knowledge and real-time PubMed research.

## Architecture Overview

**Three core components**:

1. **Vector Store** ([vector_store.py](../vector_store.py)) - Chroma DB storing curated Nigerian health myths with Gemini embeddings
2. **Search Layer** - Dual fallback strategy: first tries curated myths, then PubMed if needed
3. **RAG Agent** ([agent.py](../agent.py)) - LangChain agent with tools that returns structured verdicts (TRUE/FALSE/PARTIALLY TRUE/UNCLEAR) with confidence scores

**Data flow**: User query → Retrieve curated myths (+ optional PubMed) → Gemini generates verdict/confidence/sources → FastAPI + Jinja UI (+ optional TTS).

## Key Patterns

### Configuration Management

- All settings in [config.py](../config.py) using `@dataclass` with environment variables as defaults
- Critical: `SIMILARITY_THRESHOLD: 0.75` (70-99% match required for curated DB hits)
- Vector DB path: `./data/chroma_db` (persisted, auto-created)

### Myth Data Structure

Each myth in [data_loader.py](../data_loader.py) requires:

```python
{
    "claim": str,              # The health claim to fact-check
    "verdict": str,            # TRUE/FALSE/PARTIALLY TRUE/UNCLEAR
    "confidence": int,         # 0-100%
    "explanation": str,        # Simple language for older adults
    "sources": [str],          # WHO, NCDC, journals, etc.
    "category": str,           # malaria, covid, antibiotics, etc.
    "language": str            # "en" (multi-lang planned)
}
```

### Agent Response Format (MANDATORY)

Always follows this structure (enforced by system prompt in agent.\_get_system_prompt()):

```
**Verdict:** [TRUE / FALSE / PARTIALLY TRUE / UNCLEAR]
**Confidence:** [0-100%]
**Explanation:** [Simple language, explain medical terms]
**Why This Matters:** [Real-world consequences]
**What You Should Do Instead:** [Practical advice]
**Trusted Sources:** [List citations]
```

### Search Strategy

Agent ALWAYS uses this order:

1. `search_curated_health_myths()` first (decorator: `@tool(response_format="content_and_artifact")`)
2. Only if curated DB insufficient, call `search_pubmed_research()`
3. Both tools are LangChain tools with typed return: `Tuple[str, List[Document]]`

### PubMed Integration

- [pubmed_search.py](../pubmed_search.py) uses BioPython Entrez API
- Rate limiting: `0.34s` delay (~3 req/sec) - respect NCBI policies
- Max results: `PUBMED_MAX_RESULTS = 3` (config setting)
- Extracts: title, abstract, authors (first 3 + "et al."), journal, year, PMID, URL

## Development Workflows

### Adding a New Health Myth

1. Add dict to `CURATED_HEALTH_MYTHS` list in [data_loader.py](../data_loader.py) with required fields
2. Run `python main.py` or `uvicorn web_app:app --reload` — myths auto-index / rebuild on FastAPI startup
3. Test with: `python main.py "Your claim here"`

### Testing Claims

```bash
# CLI interface (outputs result to terminal)
python main.py "Does hot water cure malaria?"

# Web UI (HTML/CSS via Jinja)
uvicorn web_app:app --reload
```

### Debugging Agent Decisions

- Enable LangSmith tracing: set `LANGSMITH_API_KEY` in `.env` (config auto-enables if present)
- Check logs in `logs/` directory (if logging configured)
- Inspect vector DB directly: `python -c "from vector_store import HealthKnowledgeBase; from config import Config; kb = HealthKnowledgeBase(Config()); print(kb.vector_store._collection.peek(10))"`

## Critical Conventions

### Language & Accessibility

- Always explain like you're talking to older adults - simple, no jargon
- Medical terms must be defined inline: "insulin resistance (when your body can't use insulin properly)"
- Avoid acronyms without expansion

### Confidence Scoring Logic

- 90-100%: Strong scientific consensus, contradicts widely-debunked myth
- 70-89%: Good evidence, peer-reviewed research support
- 50-69%: Moderate, some uncertainty in scientific evidence
- <50%: Insufficient evidence or conflicting research

### Source Credibility Hierarchy

1. WHO official guidelines
2. Nigerian NCDC (Nigeria Centre for Disease Control)
3. Nigerian Federal Ministry of Health
4. Peer-reviewed journals (PubMed)
5. Medical associations (Nigerian Cardiac Society, etc.)
6. NEVER recommend herbal cures as proven treatments

### Myth Categories

Used for metadata filtering: `malaria`, `covid`, `diabetes`, `antibiotics`, `fever`, `hiv`, `hypertension`, `ebola`, `respiratory`, `nutrition`

## Dependencies & Versions

- LangChain ecosystem: `langchain`, `langchain-openai`, `langchain-chroma`, `langchain-community`
- Vector DB: `chromadb` (persisted in `./data/chroma_db`)
- PubMed: BioPython `biopython`
- UI: FastAPI + Jinja2 (`web_app.py`, `templates/`, `static/`)
- TTS: `gtts` (Google Text-to-Speech)
- Gemini via `google-genai`; embeddings via Gemini (`vector_store.py`)

## Environment Variables Required

```bash
GEMINI_API_KEY=...
PUBMED_EMAIL=...          # Only when PubMed enabled (see config.py)
PUBMED_ENABLED=true|false
DATABASE_URL=...          # Optional Postgres; else SQLite
ADMIN_PASSWORD=...       # Optional admin UI
```

## Common Issues & Solutions

**Issue**: "No matching health myths found" + user unhappy with answer
→ Check `SIMILARITY_THRESHOLD` (0.75 = strict), consider lowering if myths are culturally specific

**Issue**: PubMed API failures
→ Verify `PUBMED_EMAIL` is real; NCBI blocks invalid emails. Check rate limiting isn't triggered.

**Issue**: Vector DB not initializing
→ Ensure `./data/` directory is writable; Chroma auto-creates `chroma.sqlite3` and metadata folders

**Issue**: Voice output not working
→ `gtts` requires internet; check system can access Google TTS servers
