import io
import os
import tempfile
from typing import Optional, Tuple

from gtts import gTTS
from pydub import AudioSegment

from logger import logger

# Use Google GenAI SDK for transcription (if available)
try:
    from google import genai
except Exception:
    genai = None


class VoiceHandler:
    """
    Handles voice input (speech-to-text) and output (text-to-speech).
    Supports multiple audio formats and languages.
    """

    def __init__(self, api_key: str):
        """
        Initialize voice handler.

        Args:
            api_key: Gemini API key for speech-to-text (or other provider if available)
        """
        self.api_key = api_key
        self.client = None
        if genai:
            try:
                self.client = genai.Client()
            except Exception:
                import os

                os.environ["GEMINI_API_KEY"] = api_key
                self.client = genai.Client()

        # Language mapping for transcription and gTTS (output)
        self.language_codes = {
            "English": {"transcribe": "en", "gtts": "en"},
            "Pidgin": {"transcribe": "en", "gtts": "en"},  # Treat as English
            "Yoruba": {"transcribe": "yo", "gtts": "yo"},
            "Hausa": {"transcribe": "ha", "gtts": "ha"},
            "Igbo": {"transcribe": "ig", "gtts": "ig"},
        }

        # Supported audio formats
        self.supported_formats = [
            "mp3",
            "mp4",
            "mpeg",
            "mpga",
            "m4a",
            "wav",
            "webm",
            "ogg",
        ]

    def transcribe_audio(
        self, audio_file, language: str = "English", prompt: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        Transcribe audio to text using Google GenAI audio transcription (when available).

        Args:
            audio_file: Audio file object (from Streamlit file_uploader or audio_input)
            language: Language for transcription
            prompt: Optional prompt to guide transcription (e.g., medical terminology)

        Returns:
            Tuple of (transcribed_text, metadata)
        """
        try:
            # Get language code for transcription
            lang_code = self.language_codes.get(language, {}).get("transcribe", "en")

            # Prepare audio file - handle both bytes and file objects
            if isinstance(audio_file, bytes):
                audio_bytes = audio_file
            else:
                audio_bytes = audio_file.read()
                audio_file.seek(0)  # Reset file pointer

            # Get file extension
            file_extension = None
            if hasattr(audio_file, "name"):
                file_extension = audio_file.name.split(".")[-1].lower()

            # Validate format
            if file_extension and file_extension not in self.supported_formats:
                logger.warning("Unsupported audio format requested: %s", file_extension)
                return "", {"error": f"Unsupported format: {file_extension}"}

            logger.info(
                "Starting transcription: language=%s, extension=%s, bytes=%d",
                lang_code,
                file_extension,
                len(audio_bytes),
            )
            # Create temporary file for transcription
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{file_extension or 'mp3'}"
            ) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            try:
                # Use documented GenAI pattern: send prompt + inline audio bytes to models.generate_content
                if self.client is not None:
                    from google.genai import types

                    # Detect mime type from extension
                    mime_map = {
                        "mp3": "audio/mp3",
                        "wav": "audio/wav",
                        "m4a": "audio/mp4",
                        "ogg": "audio/ogg",
                        "flac": "audio/flac",
                        "aac": "audio/aac",
                    }

                    mime_type = (
                        mime_map.get(file_extension, "audio/mp3")
                        if file_extension
                        else "audio/mp3"
                    )

                    with open(temp_audio_path, "rb") as audio:
                        audio_bytes = audio.read()

                    # Build a short prompt for transcription
                    prompt = (
                        prompt
                        or f"Generate a clear transcript of this audio. Provide only the transcript text. Language hint: {lang_code}."
                    )

                    contents = [
                        prompt,
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    ]

                    try:
                        # Prefer model specified in config if available, else use gemini-2.5-flash
                        model_name = getattr(self, "model", None) or "gemini-2.5-flash"
                        # If client supports listing models, try to use first available supported model
                        try:
                            listed = self.client.models.list()
                            if listed and isinstance(listed, list) and len(listed) > 0:
                                # prefer a flash model if present
                                available = [
                                    (
                                        m.get("name")
                                        if isinstance(m, dict)
                                        else getattr(m, "name", None)
                                    )
                                    for m in listed
                                ]
                                if any("flash" in (a or "") for a in available):
                                    for a in available:
                                        if a and "flash" in a:
                                            model_name = a
                                            break
                                else:
                                    model_name = available[0]
                        except Exception:
                            pass

                        response = self.client.models.generate_content(
                            model=model_name, contents=contents
                        )
                    except Exception:
                        # Try a safe default model and surface helpful guidance
                        try:
                            response = self.client.models.generate_content(
                                model="gemini-2.5-flash", contents=contents
                            )
                        except Exception as inner_e:
                            raise RuntimeError(
                                "Generative AI audio transcription failed. See Gemini audio docs. Original error: %s"
                                % inner_e
                            )

                    # Extract transcript text
                    text = ""
                    if hasattr(response, "text") and response.text:
                        text = response.text.strip()
                    else:
                        # Fallback: inspect output structure
                        try:
                            outputs = getattr(response, "output", None)
                            if outputs and len(outputs) > 0:
                                content = outputs[0].get("content", [])
                                if content and len(content) > 0:
                                    # content elements may be dicts with 'text'
                                    first = content[0]
                                    if isinstance(first, dict):
                                        text = first.get("text", "").strip()
                                    else:
                                        text = str(first).strip()
                        except Exception:
                            text = str(response)

                    metadata = {
                        "language": lang_code,
                        "duration": None,
                        "success": True,
                    }
                    logger.info(
                        "Transcription succeeded (chars=%d)",
                        len(text) if isinstance(text, str) else 0,
                    )
                    return text, metadata

                else:
                    raise RuntimeError(
                        "Generative AI audio transcription not available. Install `google-genai` (pip install google-genai) and ensure audio transcription support is enabled."
                    )
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass

        except Exception as e:
            return "", {"error": str(e), "success": False}

    def synthesize_speech(
        self, text: str, language: str = "English", slow: bool = False
    ) -> Optional[str]:
        """
        Convert text to speech using gTTS.

        Args:
            text: Text to convert to speech
            language: Language for speech synthesis
            slow: Whether to speak slowly (good for older adults)

        Returns:
            Path to temporary audio file, or None on error
        """
        try:
            # Get language code for gTTS
            lang_code = self.language_codes.get(language, {}).get("gtts", "en")

            # Create TTS
            tts = gTTS(text=text, lang=lang_code, slow=slow)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                return fp.name

        except Exception as e:
            print(f"Text-to-speech error: {e}")
            return None

    def convert_audio_format(
        self, input_file, output_format: str = "mp3"
    ) -> Optional[bytes]:
        """
        Convert audio file to different format using pydub.
        Useful for standardizing audio before transcription.

        Args:
            input_file: Input audio file or bytes
            output_format: Desired output format

        Returns:
            Audio bytes in new format, or None on error
        """
        try:
            # Handle both bytes and file objects
            if isinstance(input_file, bytes):
                audio_bytes = input_file
            else:
                audio_bytes = input_file.read()
                input_file.seek(0)

            # Load audio
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

            # Convert to desired format
            output = io.BytesIO()
            audio.export(output, format=output_format)
            output.seek(0)

            return output.read()

        except Exception as e:
            print(f"Audio conversion error: {e}")
            return None

    def get_audio_info(self, audio_file) -> dict:
        """
        Get information about an audio file.

        Args:
            audio_file: Audio file object or bytes

        Returns:
            Dictionary with audio metadata
        """
        try:
            # Handle both bytes and file objects
            if isinstance(audio_file, bytes):
                audio_bytes = audio_file
            else:
                audio_bytes = audio_file.read()
                audio_file.seek(0)

            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

            return {
                "duration_seconds": len(audio) / 1000.0,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "frame_rate": audio.frame_rate,
                "frame_width": audio.frame_width,
            }

        except Exception as e:
            return {"error": str(e)}
