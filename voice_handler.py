import io
import os
import tempfile
from typing import Optional, Tuple

from gtts import gTTS
from openai import OpenAI
from pydub import AudioSegment


class VoiceHandler:
    """
    Handles voice input (speech-to-text) and output (text-to-speech).
    Supports multiple audio formats and languages.
    """

    def __init__(self, api_key: str):
        """
        Initialize voice handler.

        Args:
            api_key: OpenAI API key for Whisper
        """
        self.client = OpenAI(api_key=api_key)

        # Language mapping for Whisper (input) and gTTS (output)
        self.language_codes = {
            "English": {"whisper": "en", "gtts": "en"},
            "Pidgin": {"whisper": "en", "gtts": "en"},  # Treat as English
            "Yoruba": {"whisper": "yo", "gtts": "yo"},
            "Hausa": {"whisper": "ha", "gtts": "ha"},
            "Igbo": {"whisper": "ig", "gtts": "ig"},
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
        Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_file: Audio file object (from Streamlit file_uploader or audio_input)
            language: Language for transcription
            prompt: Optional prompt to guide transcription (e.g., medical terminology)

        Returns:
            Tuple of (transcribed_text, metadata)
        """
        try:
            # Get language code for Whisper
            lang_code = self.language_codes.get(language, {}).get("whisper", "en")

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
                return "", {"error": f"Unsupported format: {file_extension}"}

            # Create temporary file for Whisper API
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{file_extension or 'mp3'}"
            ) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            try:
                # Call Whisper API
                with open(temp_audio_path, "rb") as audio:
                    transcription = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        language=lang_code,
                        prompt=prompt
                        or "This is a health-related question about Nigerian healthcare.",
                        response_format="verbose_json",  # Get detailed response
                    )

                # Extract transcription and metadata
                text = transcription.text.strip()
                metadata = {
                    "language": (
                        transcription.language
                        if hasattr(transcription, "language")
                        else lang_code
                    ),
                    "duration": (
                        transcription.duration
                        if hasattr(transcription, "duration")
                        else None
                    ),
                    "success": True,
                }

                return text, metadata

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
