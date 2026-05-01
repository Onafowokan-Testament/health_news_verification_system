from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load .env before any local imports that read os.environ at import time.
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

import base64
import io
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, desc, select
from starlette.middleware.sessions import SessionMiddleware

from agent import HealthCheckAgent
from config import Config
from data_loader import get_all_myths
from database import AdminTruth, ClaimCheckRecord, engine, init_db
from logger import logger
from pubmed_search import PubMedSearcher
from vector_store import HealthKnowledgeBase
from voice_handler import VoiceHandler


@dataclass
class AppServices:
    config: Config
    knowledge_base: HealthKnowledgeBase
    agent: HealthCheckAgent
    voice_handler: VoiceHandler


def _extract_verdict(response_text: str) -> str:
    match = re.search(r"\*\*Verdict:\*\*\s*(TRUE|FALSE|PARTIALLY TRUE|UNCLEAR)", response_text, re.IGNORECASE)
    if not match:
        return "UNCLEAR"
    return match.group(1).upper()


def _audio_b64_from_file(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    return base64.b64encode(raw).decode("utf-8")


class NamedBytesIO(io.BytesIO):
    def __init__(self, initial_bytes: bytes, name: str):
        super().__init__(initial_bytes)
        self.name = name


def _sources_text_to_list(sources_text: str) -> list[str]:
    return [line.strip() for line in (sources_text or "").splitlines() if line.strip()]


def _managed_truths_as_myths() -> list[dict]:
    with Session(engine) as session:
        truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())

    myths = []
    for t in truths:
        myths.append(
            {
                "claim": t.claim,
                "verdict": t.verdict,
                "confidence": t.confidence,
                "explanation": t.explanation,
                "sources": _sources_text_to_list(t.sources_text),
                "category": t.category,
                "language": t.language,
            }
        )
    return myths


def _all_myths_for_index() -> list[dict]:
    return get_all_myths() + _managed_truths_as_myths()


def _rebuild_kb(services: AppServices) -> None:
    myths = _all_myths_for_index()
    services.knowledge_base.rebuild_index(myths)
    logger.info("Knowledge base rebuilt with %d total myths/truths", len(myths))


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info("Starting FastAPI health checker app")
    init_db()
    config = Config()
    config.validate()

    pubmed = PubMedSearcher(
        email=config.PUBMED_EMAIL or None,
        api_key=config.PUBMED_API_KEY or None,
        tool=config.PUBMED_TOOL or "MedVer",
        enabled=config.PUBMED_ENABLED,
    )
    kb = HealthKnowledgeBase(config)
    voice = VoiceHandler(config.GEMINI_API_KEY)

    myths = _all_myths_for_index()
    if kb.get_count() == 0:
        kb.index_myths(myths)
        logger.info("Indexed %d myths/truths into vector store", len(myths))
    else:
        kb.rebuild_index(myths)
        logger.info("Rebuilt index with %d myths/truths", len(myths))

    agent = HealthCheckAgent(config, kb, pubmed)
    fastapi_app.state.services = AppServices(
        config=config,
        knowledge_base=kb,
        agent=agent,
        voice_handler=voice,
    )
    logger.info("FastAPI services initialized")
    yield


app = FastAPI(title="MedVer", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "change-me-for-production"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _current_user(request: Request) -> str:
    return request.session.get("user_label", "guest")


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin", False))


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "").strip()


def _admin_enabled() -> bool:
    return bool(_admin_password())


def _create_record(
    *,
    user_label: str,
    claim: str,
    verdict: str,
    response: str,
    language: str,
) -> None:
    with Session(engine) as session:
        record = ClaimCheckRecord(
            user_label=user_label,
            claim=claim,
            verdict=verdict,
            response=response,
            language=language,
            created_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    language: str = "English"
    slow_speech: bool = True
    audio_response: bool = False

    @field_validator("message")
    @classmethod
    def strip_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Message cannot be empty")
        return s


def _form_bool(raw: str) -> bool:
    return str(raw).lower().strip() in ("true", "1", "yes", "on")


def _tts_b64(
    services: AppServices,
    text: str,
    *,
    language: str,
    slow: bool,
    want: bool,
) -> str:
    if not want:
        return ""
    audio_path = services.voice_handler.synthesize_speech(text, language=language, slow=slow)
    if not audio_path:
        return ""
    try:
        return _audio_b64_from_file(audio_path)
    finally:
        try:
            os.unlink(audio_path)
        except OSError:
            pass


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "user_label": _current_user(request),
            "is_admin": _is_admin(request),
        },
    )


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user_label": _current_user(request),
            "is_admin": _is_admin(request),
        },
    )


@app.post("/set-user")
async def set_user(request: Request, user_label: str = Form(default="guest")):
    cleaned = user_label.strip()[:100] or "guest"
    request.session["user_label"] = cleaned
    ref = request.headers.get("referer") or ""
    try:
        path = urlparse(ref).path or ""
    except Exception:
        path = ""
    if path.startswith("/chat"):
        return RedirectResponse(url="/chat", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@app.post("/api/chat")
async def api_chat(request: Request, body: ChatRequest):
    services: AppServices = request.app.state.services
    user_label = _current_user(request)
    claim = body.message.strip()
    try:
        result = services.agent.check_claim(claim)
        verdict = _extract_verdict(result["response"])
        audio_b64 = _tts_b64(
            services,
            result["response"],
            language=body.language,
            slow=body.slow_speech,
            want=body.audio_response,
        )
        _create_record(
            user_label=user_label,
            claim=claim,
            verdict=verdict,
            response=result["response"],
            language=body.language,
        )
        return JSONResponse(
            {
                "claim": claim,
                "response": result["response"],
                "verdict": verdict,
                "audio_base64": audio_b64 or None,
            }
        )
    except Exception as e:
        logger.exception("api_chat failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat-voice")
async def api_chat_voice(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form(default="English"),
    slow_speech: str = Form(default="true"),
    audio_response: str = Form(default="false"),
):
    services: AppServices = request.app.state.services
    user_label = _current_user(request)
    slow = _form_bool(slow_speech)
    want_audio = _form_bool(audio_response)

    transcription = ""
    try:
        raw_audio = await audio.read()
        if not raw_audio or len(raw_audio) < 100:
            return JSONResponse({"error": "Empty or too-short audio"}, status_code=400)
        fname = audio.filename or "voice.webm"
        named_buffer = NamedBytesIO(raw_audio, fname)
        transcription, metadata = services.voice_handler.transcribe_audio(named_buffer, language=language)
        if not metadata.get("success"):
            return JSONResponse(
                {"error": metadata.get("error", "Transcription failed")},
                status_code=400,
            )
    except (RuntimeError, ValueError, OSError) as exc:
        logger.exception("Voice transcription failed")
        return JSONResponse({"error": str(exc)}, status_code=400)

    claim = transcription.strip()
    if not claim:
        return JSONResponse({"error": "Could not understand audio"}, status_code=400)

    try:
        result = services.agent.check_claim(claim)
        verdict = _extract_verdict(result["response"])
        audio_b64 = _tts_b64(
            services,
            result["response"],
            language=language,
            slow=slow,
            want=want_audio,
        )
        _create_record(
            user_label=user_label,
            claim=claim,
            verdict=verdict,
            response=result["response"],
            language=language,
        )
        return JSONResponse(
            {
                "transcription": claim,
                "response": result["response"],
                "verdict": verdict,
                "audio_base64": audio_b64 or None,
            }
        )
    except Exception as e:
        logger.exception("api_chat_voice check failed")
        return JSONResponse({"error": str(e), "transcription": claim}, status_code=500)


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    user_label = _current_user(request)
    with Session(engine) as session:
        statement = (
            select(ClaimCheckRecord)
            .where(ClaimCheckRecord.user_label == user_label)
            .order_by(desc(ClaimCheckRecord.created_at))
            .limit(100)
        )
        records = list(session.exec(statement).all())
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user_label": user_label,
            "is_admin": _is_admin(request),
            "records": records,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user_label = _current_user(request)
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "user_label": user_label, "is_admin": _is_admin(request)},
    )


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    user_label = _current_user(request)
    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "user_label": user_label,
            "is_admin": _is_admin(request),
            "error": "",
            "admin_enabled": _admin_enabled(),
        },
    )


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, password: str = Form(default="")):
    user_label = _current_user(request)
    if not _admin_enabled():
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request,
                "user_label": user_label,
                "is_admin": False,
                "error": "ADMIN_PASSWORD is not configured on the server.",
                "admin_enabled": False,
            },
        )
    if password != _admin_password():
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request,
                "user_label": user_label,
                "is_admin": False,
                "error": "Invalid admin password.",
                "admin_enabled": True,
            },
        )
    request.session["is_admin"] = True
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/logout")
async def admin_logout(request: Request):
    request.session["is_admin"] = False
    return RedirectResponse(url="/", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    user_label = _current_user(request)
    with Session(engine) as session:
        truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user_label": user_label,
            "is_admin": True,
            "truths": truths,
            "message": "",
            "error": "",
        },
    )


@app.post("/admin/add-truth", response_class=HTMLResponse)
async def admin_add_truth(
    request: Request,
    claim: str = Form(default=""),
    verdict: str = Form(default="TRUE"),
    confidence: int = Form(default=90),
    explanation: str = Form(default=""),
    sources_text: str = Form(default=""),
    category: str = Form(default="general"),
    language: str = Form(default="en"),
):
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    user_label = _current_user(request)
    claim = claim.strip()
    explanation = explanation.strip()
    if not claim or not explanation:
        with Session(engine) as session:
            truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "user_label": user_label,
                "is_admin": True,
                "truths": truths,
                "message": "",
                "error": "Claim and explanation are required.",
            },
        )

    with Session(engine) as session:
        truth = AdminTruth(
            claim=claim,
            verdict=verdict.strip().upper()[:30] or "TRUE",
            confidence=max(0, min(int(confidence), 100)),
            explanation=explanation,
            sources_text=sources_text.strip(),
            category=category.strip()[:100] or "general",
            language=language.strip()[:20] or "en",
        )
        session.add(truth)
        session.commit()

    services: AppServices = request.app.state.services
    _rebuild_kb(services)

    with Session(engine) as session:
        truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user_label": user_label,
            "is_admin": True,
            "truths": truths,
            "message": "Truth added and index refreshed.",
            "error": "",
        },
    )


@app.post("/admin/delete-truth")
async def admin_delete_truth(request: Request, truth_id: int = Form(...)):
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    with Session(engine) as session:
        truth = session.get(AdminTruth, truth_id)
        if truth:
            session.delete(truth)
            session.commit()

    services: AppServices = request.app.state.services
    _rebuild_kb(services)
    return RedirectResponse(url="/admin", status_code=303)
