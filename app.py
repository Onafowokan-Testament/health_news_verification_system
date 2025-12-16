import os

import streamlit as st
from dotenv import load_dotenv

from vector_store import HealthKnowledgeBase

load_dotenv()
from agent import HealthCheckAgent
from config import Config
from data_loader import get_all_myths
from pubmed_search import PubMedSearcher
from voice_handler import VoiceHandler

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


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

    # Initialize session state
    if "agent" not in st.session_state:
        with st.spinner("🔧 Loading system..."):
            try:
                # Load configuration
                config = Config()
                config.validate()

                # Initialize components
                pubmed = PubMedSearcher(config.PUBMED_EMAIL)
                kb = HealthKnowledgeBase(config)
                voice = VoiceHandler(config.OPENAI_API_KEY)

                # Index myths if database is empty
                if kb.get_count() == 0:
                    myths = get_all_myths()
                    kb.index_myths(myths)

                # Create agent
                st.session_state.agent = HealthCheckAgent(config, kb, pubmed)
                st.session_state.voice_handler = voice
                st.session_state.config = config

                st.success("✓ System ready!")
            except Exception as e:
                st.error(f"Initialization error: {e}")
                st.stop()

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
        2. **Upload:** Or upload a pre-recorded audio file
        3. **Check:** Review the transcription before checking
        
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
        - OpenAI Whisper for voice input
        
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
    tab1, tab2, tab3 = st.tabs(
        ["💬 Type Your Question", "🎤 Record Audio", "📁 Upload Audio File"]
    )

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
            "Click the microphone to start recording. Speak clearly and state your complete question."
        )

        # Audio recorder component
        audio_bytes = st.audio_input("Click the microphone to record")

        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("📝 Transcribe Recording", key="transcribe_recorded"):
                    with st.spinner("🎧 Transcribing audio..."):
                        try:
                            # Transcribe audio bytes directly
                            voice_handler = st.session_state.voice_handler
                            transcribed_text, metadata = voice_handler.transcribe_audio(
                                audio_bytes, language=language
                            )

                            if metadata.get("success", False):
                                display_audio_status(
                                    f"Transcribed successfully in {metadata.get('duration', 'N/A')} seconds",
                                    True,
                                )

                                st.markdown(
                                    f'<div class="transcription-box">'
                                    f"<strong>Transcription:</strong><br>{transcribed_text}"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

                                st.session_state.transcribed_claim = transcribed_text
                            else:
                                display_audio_status(
                                    f"Transcription failed: {metadata.get('error', 'Unknown error')}",
                                    False,
                                )

                        except Exception as e:
                            st.error(f"Error: {e}")

            with col2:
                if (
                    "transcribed_claim" in st.session_state
                    and st.session_state.transcribed_claim
                ):
                    if st.button("✅ Check Transcribed Claim", key="check_recorded"):
                        claim_to_check = st.session_state.transcribed_claim

    # Tab 3: Upload Audio File
    with tab3:
        st.subheader("Upload Audio File")
        st.markdown("Upload a pre-recorded audio file (MP3, WAV, M4A, OGG, etc.)")

        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["mp3", "wav", "m4a", "ogg", "webm", "mp4", "mpeg"],
            help="Maximum file size: 25 MB",
        )

        if uploaded_file:
            st.audio(uploaded_file)

            # Show audio info
            with st.expander("📊 Audio File Info"):
                voice_handler = st.session_state.voice_handler
                audio_info = voice_handler.get_audio_info(uploaded_file)

                if "error" not in audio_info:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Duration", f"{audio_info.get('duration_seconds', 0):.1f}s"
                        )
                    with col2:
                        st.metric("Channels", audio_info.get("channels", "N/A"))
                    with col3:
                        st.metric(
                            "Sample Rate", f"{audio_info.get('frame_rate', 0)} Hz"
                        )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("📝 Transcribe File", key="transcribe_file"):
                    with st.spinner("🎧 Transcribing audio..."):
                        try:
                            voice_handler = st.session_state.voice_handler
                            transcribed_text, metadata = voice_handler.transcribe_audio(
                                uploaded_file, language=language
                            )

                            if metadata.get("success", False):
                                display_audio_status(
                                    f"Transcribed successfully! Language: {metadata.get('language', 'Unknown')}",
                                    True,
                                )

                                st.markdown(
                                    f'<div class="transcription-box">'
                                    f"<strong>Transcription:</strong><br>{transcribed_text}"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

                                st.session_state.uploaded_transcription = (
                                    transcribed_text
                                )
                            else:
                                display_audio_status(
                                    f"Transcription failed: {metadata.get('error', 'Unknown error')}",
                                    False,
                                )

                        except Exception as e:
                            st.error(f"Error: {e}")

            with col2:
                if (
                    "uploaded_transcription" in st.session_state
                    and st.session_state.uploaded_transcription
                ):
                    if st.button("✅ Check Transcribed Claim", key="check_uploaded"):
                        claim_to_check = st.session_state.uploaded_transcription

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
