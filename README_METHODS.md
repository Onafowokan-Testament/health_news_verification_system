# Project Methodology & Data Details

## 1. What data did you use, how did you get the data, and where?

- **Curated Dataset:**  
  The core dataset is a manually curated list of common Nigerian health myths, found in the `CURATED_HEALTH_MYTHS` list in [data_loader.py](data_loader.py).  
  Each entry includes:  
  - `claim`: The health claim to fact-check  
  - `verdict`: TRUE / FALSE / PARTIALLY TRUE / UNCLEAR  
  - `confidence`: 0-100%  
  - `explanation`: Simple, accessible language  
  - `sources`: Trusted references (WHO, NCDC, Nigerian Ministry of Health, peer-reviewed journals)  
  - `category`: e.g., malaria, covid, antibiotics  
  - `language`: e.g., "en"  

- **Data Collection:**  
  Myths were gathered from:
  - WHO and NCDC myth-busting pages
  - Nigerian Ministry of Health advisories
  - Peer-reviewed medical journals
  - Local news and public health campaigns
  - Community interviews and reports of common misconceptions

- **Where is the data?**  
  - The raw, human-readable dataset is in [data_loader.py](data_loader.py) as a Python list of dictionaries.
  - The vectorized version (for fast search) is stored in `data/chroma_db/` (auto-generated).

## 2. How did you clean the data?

- All entries are standardized to include every required field.
- Explanations are rewritten in plain language, with medical terms explained inline.
- Sources are checked for credibility and formatted as URLs or official document titles.
- The loader validates entries for completeness and correct types.
- Duplicate or ambiguous myths are removed or clarified.

## 3. What do I show my supervisor as the dataset?

- Show the `CURATED_HEALTH_MYTHS` list in [data_loader.py](data_loader.py).
- This is the authoritative, human-readable dataset.
- Optionally, show the vector DB files in `data/chroma_db/` (but these are not human-readable).

## 4. How did you test the accuracy of the system (F1 score, etc.)?

- The system is a retrieval-augmented generator (RAG), not a pure classifier.
- For evaluation:
  - Prepare a test set of health claims (labeled as true/false/unclear).
  - Run each claim through the system and record the verdict.
  - Compare system verdicts to ground truth to compute precision, recall, and F1 score.
  - For PubMed retrieval, assess the relevance of returned articles and the correctness of generated explanations.
- Note: No automated F1 score is included by default; you must create a labeled test set and script for this.

## 5. Why use RAG instead of BERT?

- **RAG** (Retrieval-Augmented Generation) combines:
  - Fast retrieval from a curated, updatable knowledge base (for instant, locally relevant answers)
  - Real-time search of PubMed for new research
  - LLM-based generation for clear, contextual explanations and citations
- **BERT** is a static encoder, good for classification or similarity, but cannot generate explanations or cite new research.
- RAG is better for fact-checking, transparency, and up-to-date, source-backed answers.

## 6. What makes it Nigerian-based?

- The curated myths are specific to Nigerian health misinformation and cultural context.
- Sources include Nigerian health authorities (NCDC, Ministry of Health, NACA).
- Categories reflect health issues prevalent in Nigeria (malaria, fever, typhoid, etc.).
- Explanations are tailored for Nigerian older adults, using local language and examples.

## 7. What LLM was used in particular?

- The system uses Google’s Gemini model (default: `gemini-2.5-flash`), as set in the `.env` file and [config.py](config.py).
- Embeddings for the vector store use Gemini’s `gemini-text-embedding-1.0` model.
- (If you want to use OpenAI’s GPT-4o or other models, adapters can be added.)
