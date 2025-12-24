# Nigerian Health Claim Checker

A simple, accessible tool to help older adults verify health claims using trusted guidance and medical research.

✅ Easy for non-technical users

- Record your question with the microphone and the app will automatically transcribe and check the claim for you.
- Or type a claim into the box and click Check.
- Results show a clear verdict (TRUE / FALSE / PARTIALLY TRUE / UNCLEAR), a short explanation, and trusted sources.

## How to run (non-technical)

1. Install Python (version 3.9+). If you already have it, skip this step.
2. Open a command prompt in this folder (where this README is).
3. Create and activate a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
4. Install dependencies:
   - `pip install -r requirements.txt`
5. Create a `.env` file with at least these values:
   - `GEMINI_API_KEY=your_gemini_api_key_here` (required)
   - `PUBMED_EMAIL=you@example.com` (required by PubMed API)
6. Start the app:
   - `streamlit run app.py`
7. The app will open in your browser. Click the microphone and speak; the app will automatically transcribe and verify your claim.

## What the app does (simple explanation)

- The app has a small database of common Nigerian health myths and uses PubMed for scientific research when needed.
- When you record audio, the system converts it to text (transcription), then checks that text against the database and research to provide a short, clear verdict and advice.
- The app is designed to speak clearly and explain things using plain language so it’s easy to understand.

## Main parts of the code (for maintainers)

- `app.py` — Streamlit UI and user interaction. Handles recording, transcription, and showing results.
- `agent.py` — The "thinking" part. It uses a small curated database first, then searches PubMed if needed, and formats the final verdict.
- `vector_store.py` & `data_loader.py` — Store and provide the curated myths used for instant answers.
- `pubmed_search.py` — A small helper that fetches recent PubMed papers when needed.
- `voice_handler.py` — Handles speech-to-text and text-to-speech.
- `config.py` — Configuration settings (API keys, model names, thresholds).

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

## Privacy & safety

- We don’t store audio recordings permanently. The app transcribes and processes audio to generate a short result.
- This tool is for informational purposes only and does not replace professional medical advice.

## Logging & debugging

- The app logs runtime events to the terminal using `loguru` (initialization steps, transcription events, model calls, PubMed queries and errors).
- Run the app with `streamlit run app.py` and watch the terminal to follow what the app is doing.

## Need more help?

Tell me if you want:

- A guided walkthrough added to the app UI for first-time users
- A model switcher to try Gemini and OpenAI interchangeably
- Simpler installer scripts for non-technical users

Thank you — I can also update the app to show spoken results back to the user if you'd like audio feedback after the verdict.
