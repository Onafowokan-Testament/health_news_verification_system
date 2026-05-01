# MedVer

A simple, accessible tool (**MedVer**) to help older adults verify health claims using trusted guidance and, optionally, medical literature from PubMed.

✅ Easy for non-technical users

- Open **Chat** (`/chat`): type a claim or tap the **microphone** to speak — your browser records audio only (no video upload).
- The landing page (`/`) explains the product; History saves past checks per user name.

## How to run (non-technical)

1. Install Python (version 3.9+). If you already have it, skip this step.
2. Open a command prompt in this folder (where this README is).
3. Create and activate a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
4. Install dependencies:
   - `pip install -r requirements.txt`
5. Create a `.env` file with at least these values:
   - `GEMINI_API_KEY=your_gemini_api_key_here` (required)
   - `SESSION_SECRET=replace_with_a_long_random_secret` (recommended for the FastAPI app)

**PubMed (optional):** By default MedVer runs **without** PubMed so you do not need to supply an Entrez contact email. Verdicts use your curated knowledge base (plus Gemini). To enable PubMed search, add:

   - `PUBMED_ENABLED=true`
   - `PUBMED_EMAIL=an-email-you-own@example.com` (NCBI asks developers to identify their application)

Optional Entrez tuning:

   - `PUBMED_API_KEY=` — [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/) (higher rate limits)
   - `PUBMED_TOOL=MedVer` — short application name sent to NCBI (default is MedVer)

6. Start the web app:

   - `uvicorn web_app:app --reload`

7. Open `http://127.0.0.1:8000` for the **landing page**, or go directly to **`http://127.0.0.1:8000/chat`** for the ChatGPT-style chat UI.

MedVer is built with **FastAPI**, **Jinja2** templates, and **CSS** (`templates/`, `static/`).

Features:

- Chat-first UI with conversational layout
- Voice via microphone button (MediaRecorder; transcribed server-side)
- AI verdict with evidence-based explanation
- Optional audio response
- Multi-page UI (landing, chat, history, about)
- User-based persistent history (SQLite via SQLModel)
- PostgreSQL support via `DATABASE_URL` (falls back to SQLite if not set)
- Admin-only truth management page (`/admin`)

### Database configuration

The app supports both SQLite and PostgreSQL:

- **Default (local):** SQLite at `data/app.db`
- **Production:** set `DATABASE_URL` in `.env`, for example:
  - `DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/health_checker`

### Admin configuration

To enable admin truth management, set:

- `ADMIN_PASSWORD=your_secure_admin_password`

Then open `/admin/login` and authenticate. Admin can:
- Add trusted truth records
- Delete admin-added records
- Trigger automatic vector index refresh after each change

## What the app does (simple explanation)

- The app has a small database of common Nigerian health myths and uses PubMed for scientific research when needed.
- When you record audio, the system converts it to text (transcription), then checks that text against the database and research to provide a short, clear verdict and advice.
- The app is designed to speak clearly and explain things using plain language so it’s easy to understand.

## Main parts of the code (for maintainers)

- `web_app.py` — FastAPI app: landing (`/`), chat (`/chat`), JSON APIs (`/api/chat`, `/api/chat-voice`), admin, history.
- `agent.py` — Retrieval + Gemini generation for verdicts.
- `vector_store.py` & `data_loader.py` — Curated myths and Chroma vector search.
- `pubmed_search.py` — PubMed (Entrez) when enabled.
- `voice_handler.py` — Speech-to-text (Gemini) and text-to-speech (gTTS); optional audio conversion uses pydub.
- `database.py` — SQLModel tables (history, admin truths).
- `config.py` — Environment-driven settings.

## Auto-transcribe & auto-verify

The app now automatically transcribes recordings and immediately checks the transcribed text — no more extra buttons needed. This makes it simpler for users who just want to speak and get an answer.

## Using Gemini API instead of OpenAI

Yes — it’s possible to use Google’s Gemini models instead of OpenAI, but it requires a few changes:

1. **API keys**: Add your Gemini API key (for example `GEMINI_API_KEY`) to the `.env` file.
2. **Install the Gemini client**: Add the official Google Gemini or Vertex AI client as a dependency (check the vendor docs for the correct package).
3. **Update the model wrapper**: The app now uses Gemini as the only model provider via `gemini_client.py`.
4. **Embeddings**: The app still uses OpenAI embeddings by default (`text-embedding-3-large`). If you want embeddings from a different provider, we can add an adapter for that also.

If you want, I can make a small adapter in `agent.py` so you can switch models by setting a config value like `MODEL_PROVIDER = 'openai'|'gemini'`, and I’ll show the exact code changes.

## Using Gemini (step-by-step)

To use Gemini instead of OpenAI, set the following environment variables in your `.env` file:

- `MODEL_PROVIDER=gemini`
- `GEMINI_API_KEY=your_gemini_api_key_here`
- Optionally `GEMINI_MODEL=gemini-2.5-flash` (or your preferred Gemini model name – use `client.models.list()` if unsure)

Also install the Gemini client package:

- `pip install google-genai`

I added a small `gemini_client.py` adapter that calls Gemini for chat completions and automatically includes curated DB and PubMed results in the prompt. The `agent.py` will use Gemini when `MODEL_PROVIDER=gemini`.

## Logging & debugging

- The app logs runtime events to the terminal using `loguru`.
- Run `uvicorn web_app:app --reload` and watch the terminal for indexing, Gemini calls, and PubMed (when enabled).

## Privacy & safety

- We don’t store audio recordings permanently. The app transcribes and processes audio to generate a short result.
- This tool is for informational purposes only and does not replace professional medical advice.

### Python 3.13 and audio

The standard library `audioop` module was removed in Python 3.13. This project depends on `audioop-lts` so `pydub` keeps working. If you use audio format conversion heavily, install [FFmpeg](https://ffmpeg.org/) and ensure `ffmpeg` is on your `PATH`.

## Need more help?

Tell me if you want:

- A guided walkthrough added to the app UI for first-time users
- A model switcher to try Gemini and OpenAI interchangeably
- Simpler installer scripts for non-technical users

Thank you — I can also update the app to show spoken results back to the user if you'd like audio feedback after the verdict.
