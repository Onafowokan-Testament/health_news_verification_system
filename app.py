import os

import streamlit as st
from dotenv import load_dotenv

from logger import logger
from vector_store import HealthKnowledgeBase

load_dotenv()
from agent import HealthCheckAgent
from config import Config
from data_loader import get_all_myths
from pubmed_search import PubMedSearcher
from voice_handler import VoiceHandler

# Using Gemini for ML services; GEMINI_API_KEY is validated in Config


def initialize_app():
    """Initialize the Streamlit app."""
    st.set_page_config(
        page_title="Nigerian Health Claim Checker", page_icon="🏥", layout="wide"
    )

    # Custom CSS
    st.markdown(
        """
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
        }
        .verdict-false {
            background-color: #f8d7da;
            padding: 15px;
            border-radius: 5px;
            border-left: 5px solid #dc3545;
            margin: 10px 0;
        }
        .verdict-true {
            background-color: #d4edda;
            padding: 15px;
            border-radius: 5px;
            border-left: 5px solid #28a745;
            margin: 10px 0;
        }
        .verdict-partial {
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            border-left: 5px solid #ffc107;
            margin: 10px 0;
        }
        .transcription-box {
            background-color: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            border-left: 3px solid #2196F3;
            margin: 10px 0;
        }
        .audio-status {
            background-color: #f0f0f0;
            padding: 8px;
            border-radius: 4px;
            font-size: 0.9em;
            margin: 5px 0;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def display_audio_status(status: str, is_success: bool = True):
    """Display audio processing status."""
    color = "#28a745" if is_success else "#dc3545"
    icon = "✓" if is_success else "✗"
    st.markdown(
        f'<div class="audio-status" style="border-left: 3px solid {color};">'
        f"{icon} {status}"
        f"</div>",
        unsafe_allow_html=True,
    )


def main():
    """Main Streamlit app with voice input."""
    initialize_app()

    # Header
    st.markdown(
        '<h1 class="main-header">🏥 Nigerian Health Claim Checker</h1>',
        unsafe_allow_html=True,
    )
    st.markdown("### Check if health claims you've heard are true or false")
    st.markdown("**NEW: Now with voice input! 🎤**")

    # Ensure configuration is available early to avoid missing session_state keys
    if "config" not in st.session_state:
        # If running on Streamlit Cloud, the user may have set GEMINI_API_KEY in st.secrets
        try:
            if getattr(st, "secrets", None) and st.secrets.get("GEMINI_API_KEY"):
                os.environ.setdefault("GEMINI_API_KEY", st.secrets["GEMINI_API_KEY"])
        except Exception:
            # Defensive: if secrets are not available or access fails, continue
            pass

        st.session_state.config = Config()
        try:
            st.session_state.config.validate()
            logger.info("Config validated")
        except Exception as e:
            logger.exception("Config validation failed: %s", e)
            st.error(
                "Configuration error: GEMINI_API_KEY is required. Set it in Streamlit Secrets or environment variables. See README for deployment steps."
            )
            # Stop further execution so we don't access uninitialized components
            st.stop()

    # Initialize session state components (only if agent missing)
    if "agent" not in st.session_state:
        with st.spinner("🔧 Loading system..."):
            try:
                logger.info("Loading system components in Streamlit UI")
                config = st.session_state.config

                # Initialize components
                pubmed = PubMedSearcher(config.PUBMED_EMAIL)
                kb = HealthKnowledgeBase(config)
                voice = VoiceHandler(config.GEMINI_API_KEY)
                logger.info("Components initialized: PubMed, KB, VoiceHandler")

                # Index myths if database is empty
                if kb.get_count() == 0:
                    logger.info("Indexing myths into KB from data_loader")
                    myths = get_all_myths()
                    kb.index_myths(myths)

                # Create agent
                st.session_state.agent = HealthCheckAgent(config, kb, pubmed)
                st.session_state.voice_handler = voice

                st.success("✓ System ready!")
                logger.info("Streamlit system ready")
            except Exception as e:
                logger.exception("Initialization error in Streamlit app: %s", e)
                st.error(f"Initialization error: {e}")
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        language = st.selectbox(
            "Select Language",
            st.session_state.config.SUPPORTED_LANGUAGES,
            index=0,
            help="Language for voice input/output",
        )

        enable_audio_output = st.checkbox("Enable Audio Response", value=True)
        slow_speech = st.checkbox(
            "Speak Slowly", value=True, help="Recommended for older adults"
        )

        st.markdown("---")
        st.markdown("### 🎤 Voice Input Guide")
        st.info(
            """
        **How to use voice input:**
        
        1. **Record:** Click the microphone and speak your question clearly
        2. **Check:** Review the transcription before checking
        
        **Tips for best results:**
        - Speak clearly and slowly
        - Minimize background noise
        - Keep questions under 30 seconds
        - State the full claim/question
        """
        )

        st.markdown("---")
        st.markdown("### About")
        st.info(
            """
        This system helps verify health claims using:
        - Curated Nigerian health myths database
        - PubMed medical research
        - WHO and NCDC guidelines
        - Gemini (Google GenAI) for voice transcription and generation
        
        ⚠️ This is not a substitute for medical advice. 
        Always consult healthcare professionals.
        """
        )

        st.markdown("---")
        st.markdown("### Quick Examples")
        example_claims = [
            "Hot water cures malaria",
            "Sugar causes diabetes",
            "Antibiotics cure flu",
            "Bitter kola cures COVID-19",
        ]

        for example in example_claims:
            if st.button(example, key=f"example_{example}"):
                st.session_state.current_claim = example

    # Main content
    st.markdown("---")

    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["💬 Type Your Question", "🎤 Record Audio"])

    claim_to_check = None

    # Tab 1: Text Input
    with tab1:
        st.subheader("Type Your Health Claim")
        claim_input = st.text_area(
            "What health claim would you like to check?",
            value=st.session_state.get("current_claim", ""),
            height=100,
            placeholder="Example: Does hot water cure malaria?",
            key="text_input",
        )

        if st.button("🔍 Check This Claim", key="check_text", type="primary"):
            claim_to_check = claim_input

    # Tab 2: Record Audio (Live Recording)
    with tab2:
        st.subheader("Record Your Question")
        st.markdown(
            "Click the microphone to start recording. Speak clearly and state your complete question. The app will automatically transcribe and verify what you say once recording finishes."
        )

        # Audio recorder component
        audio_bytes = st.audio_input("Click the microphone to record")

        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")

            # Compute a simple hash for the recording so we don't retranscribe the same audio repeatedly
            try:
                import hashlib

                if hasattr(audio_bytes, "getbuffer"):
                    data = audio_bytes.getbuffer().tobytes()
                elif hasattr(audio_bytes, "getvalue"):
                    data = audio_bytes.getvalue()
                else:
                    # Fallback
                    audio_bytes.seek(0)
                    data = audio_bytes.read()

                audio_hash = hashlib.sha256(data).hexdigest()
            except Exception:
                audio_hash = None

            # Transcribe once per unique recording and then automatically set for checking
            if audio_hash and st.session_state.get("last_recorded_hash") != audio_hash:
                with st.spinner("🎧 Transcribing and checking claim..."):
                    try:
                        voice_handler = st.session_state.voice_handler
                        transcribed_text, metadata = voice_handler.transcribe_audio(
                            audio_bytes, language=language
                        )

                        if metadata.get("success", False):
                            display_audio_status(
                                "Transcribed successfully",
                                True,
                            )

                            st.markdown(
                                f'<div class="transcription-box">'
                                f"<strong>Transcription:</strong><br>{transcribed_text}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                            st.session_state.transcribed_claim = transcribed_text
                            st.session_state.last_recorded_hash = audio_hash

                            # Automatically set claim_to_check so the claim will be analyzed below
                            claim_to_check = transcribed_text
                        else:
                            display_audio_status(
                                f"Transcription failed: {metadata.get('error', 'Unknown error')}",
                                False,
                            )

                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                # If already transcribed earlier during this session, show the transcription and set it for checking
                if (
                    "transcribed_claim" in st.session_state
                    and st.session_state.transcribed_claim
                ):
                    st.markdown(
                        f'<div class="transcription-box">'
                        f"<strong>Transcription:</strong><br>{st.session_state.transcribed_claim}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    claim_to_check = st.session_state.transcribed_claim

    # (Upload audio file functionality removed to simplify UI and avoid file uploads)
    # The upload tab was removed per user preference.

    # Process claim if one was submitted
    if claim_to_check and claim_to_check.strip():
        st.markdown("---")

        with st.spinner("🔎 Analyzing claim..."):
            try:
                result = st.session_state.agent.check_claim(claim_to_check)

                # Display results
                st.markdown("## 📊 Results")

                response_text = result["response"]

                # Parse verdict
                verdict = "UNCLEAR"
                verdict_class = "verdict-partial"
                if (
                    "Verdict:** FALSE" in response_text
                    or "Verdict:** False" in response_text
                ):
                    verdict = "FALSE"
                    verdict_class = "verdict-false"
                elif (
                    "Verdict:** TRUE" in response_text
                    or "Verdict:** True" in response_text
                ):
                    verdict = "TRUE"
                    verdict_class = "verdict-true"
                elif "Verdict:** PARTIALLY TRUE" in response_text:
                    verdict = "PARTIALLY TRUE"
                    verdict_class = "verdict-partial"

                # Display result
                st.markdown(
                    f'<div class="{verdict_class}">{response_text}</div>',
                    unsafe_allow_html=True,
                )

                # Audio output
                if enable_audio_output:
                    st.markdown("### 🔊 Audio Response")
                    with st.spinner("Generating audio response..."):
                        voice_handler = st.session_state.voice_handler
                        audio_path = voice_handler.synthesize_speech(
                            response_text, language=language, slow=slow_speech
                        )

                        if audio_path:
                            st.audio(audio_path)
                            # Clean up
                            try:
                                os.unlink(audio_path)
                            except:
                                pass
                        else:
                            st.warning("Could not generate audio response")

                # Add to history
                if "history" not in st.session_state:
                    st.session_state.history = []

                st.session_state.history.append(
                    {
                        "claim": claim_to_check,
                        "verdict": verdict,
                        "response": response_text,
                    }
                )

                # Clear states
                st.session_state.current_claim = ""
                if "transcribed_claim" in st.session_state:
                    del st.session_state.transcribed_claim
                if "uploaded_transcription" in st.session_state:
                    del st.session_state.uploaded_transcription

            except Exception as e:
                st.error(f"Error processing claim: {e}")
                st.exception(e)

    # History section
    if st.session_state.get("history"):
        st.markdown("---")
        st.markdown("### 📜 Recent Checks")

        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            with st.expander(
                f"{item['claim'][:60]}..." if len(item["claim"]) > 60 else item["claim"]
            ):
                st.markdown(f"**Verdict:** {item['verdict']}")
                st.markdown(
                    item["response"][:200] + "..."
                    if len(item["response"]) > 200
                    else item["response"]
                )


if __name__ == "__main__":
    main()
