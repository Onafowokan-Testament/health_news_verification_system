"""Gemini client wrapper using the official Google GenAI SDK (`google-genai`).

This wrapper follows the Quickstart: https://ai.google.dev/gemini-api/docs/quickstart
Install: `pip install google-genai`
"""

from logger import logger

try:
    from google import genai
except Exception:
    genai = None


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
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
        logger.info(
            "Calling Gemini models.generate_content with model=%s prompt_len=%d",
            self.model,
            len(prompt),
        )

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
        except Exception as e:
            # Try to surface a helpful error message when the model is not found or unsupported
            err_text = str(e)
            logger.exception("Gemini generate_content error: %s", err_text)
            if "404" in err_text or "not found" in err_text.lower():
                available = self._list_models()
                sample = (
                    ", ".join(available[:5])
                    if available
                    else "(could not fetch models)"
                )
                raise RuntimeError(
                    f"Model {self.model} not found or not supported for generate_content. "
                    f"Available models (sample): {sample}. Try setting GEMINI_MODEL to a supported model like 'gemini-2.5-flash'"
                )
            raise

        # Extract text safely (SDK exposes `.text` on simple responses)
        text = ""
        if hasattr(response, "text") and response.text:
            text = response.text
        else:
            # Fallback to inspect response structure
            try:
                outputs = getattr(response, "output", None)
                if outputs and len(outputs) > 0:
                    content = outputs[0].get("content", [])
                    if content and len(content) > 0:
                        first = content[0]
                        if isinstance(first, dict):
                            text = first.get("text", "")
                        else:
                            text = str(first)
            except Exception:
                text = str(response)

        logger.info(
            "Gemini response length: %d", len(text) if isinstance(text, str) else 0
        )
        return text
