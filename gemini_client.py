"""Gemini client wrapper using the official Google GenAI SDK (`google-genai`).

This wrapper follows the Quickstart: https://ai.google.dev/gemini-api/docs/quickstart
Install: `pip install google-genai`
"""

from logger import logger

try:
    from google import genai
except Exception:
    genai = None


def _extract_response_text(response) -> str:
    """Best-effort extraction for Gemini SDK response shapes."""
    if response is None:
        return ""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None)
    if candidates:
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None and isinstance(candidate, dict):
                content = candidate.get("content")

            parts = getattr(content, "parts", None)
            if parts is None and isinstance(content, dict):
                parts = content.get("parts")

            if not parts:
                continue

            collected: list[str] = []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text is None and isinstance(part, dict):
                    part_text = part.get("text")
                if part_text:
                    collected.append(str(part_text))

            joined = "".join(collected).strip()
            if joined:
                return joined

    outputs = getattr(response, "output", None)
    if outputs and len(outputs) > 0:
        try:
            content = outputs[0].get("content", [])
            if content and len(content) > 0:
                first = content[0]
                if isinstance(first, dict):
                    return str(first.get("text", "")).strip()
                return str(first).strip()
        except Exception:
            pass

    return str(response).strip()


def _friendly_model_error(exc: Exception) -> str:
    """Convert Gemini/API failures into a short user-facing message."""
    err_text = str(exc).strip()
    low = err_text.lower()

    if "503" in low or "unavailable" in low or "high demand" in low:
        return (
            "The AI service is busy right now. I received your question, but "
            "could not generate a reply. Please try again in a minute."
        )

    if "429" in low or "rate limit" in low:
        return (
            "The AI service is receiving too many requests right now. Please "
            "wait a moment and try again."
        )

    if "401" in low or "403" in low or "permission" in low or "api key" in low:
        return (
            "The AI service is not configured correctly on the server. Please "
            "contact the app owner."
        )

    if "404" in low or "not found" in low:
        return (
            "The selected AI model is not available right now. Please try again "
            "later or update the model setting."
        )

    return (
        "I could not generate a reply right now. Please try again in a minute."
    )


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.client = None
        if genai:
            # The client will read GEMINI_API_KEY from the environment by default
            try:
                self.client = genai.Client()
                logger.info("Gemini client initialized using environment API key")
            except Exception:
                # If the environment is not set, set it and retry
                import os

                os.environ["GEMINI_API_KEY"] = api_key
                self.client = genai.Client()
                logger.info("Gemini client initialized after setting env var")

    def _list_models(self) -> list:
        """Return a list of available model ids from the Gemini client."""
        try:
            models = self.client.models.list()
            ids = [
                m.get("name") if isinstance(m, dict) else getattr(m, "name", None)
                for m in models
            ]
            logger.info("Available Gemini models sample: %s", ids[:6])
            return [m for m in ids if m]
        except Exception as e:
            logger.exception("Could not list Gemini models: %s", e)
            return []

    def _build_model_candidates(self) -> list[str]:
        """Return preferred model names in order."""
        preferred = [
            self.model,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ]
        available = self._list_models()
        if available:
            preferred = [name for name in preferred if name in available] + [
                name for name in available if name not in preferred
            ]

        candidates: list[str] = []
        for name in preferred:
            if name and name not in candidates:
                candidates.append(name)
        return candidates

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a chat-style request to Gemini and return the assistant text.

        Uses `models.generate_content`. On 404 (model not supported) it lists available models
        and raises a clear RuntimeError with suggestions.
        """
        if not self.client:
            raise RuntimeError(
                "google-genai package not installed. Install with: `pip install google-genai`"
            )

        prompt = system_prompt + "\n\n" + user_message
        candidates = self._build_model_candidates()
        last_error: Exception | None = None

        for model_name in candidates:
            logger.info(
                "Calling Gemini models.generate_content with model=%s prompt_len=%d",
                model_name,
                len(prompt),
            )
            try:
                response = self.client.models.generate_content(
                    model=model_name, contents=prompt
                )
                text = _extract_response_text(response)
                if not text:
                    logger.warning(
                        "Gemini returned an empty response payload for model=%s: %r",
                        model_name,
                        response,
                    )
                    continue

                self.model = model_name
                logger.info(
                    "Gemini response length: %d",
                    len(text) if isinstance(text, str) else 0,
                )
                return text
            except Exception as e:
                last_error = e
                err_text = str(e)
                logger.exception(
                    "Gemini generate_content error for model=%s: %s",
                    model_name,
                    err_text,
                )
                if "404" in err_text or "not found" in err_text.lower():
                    logger.warning("Skipping unavailable model: %s", model_name)
                    continue
                if "503" in err_text or "429" in err_text or "unavailable" in err_text.lower():
                    logger.warning(
                        "Gemini model %s is overloaded; trying next fallback model",
                        model_name,
                    )
                    continue
                return _friendly_model_error(e)

        if last_error is not None:
            return _friendly_model_error(last_error)
        return "I couldn't generate a response from Gemini right now. Please try again."
