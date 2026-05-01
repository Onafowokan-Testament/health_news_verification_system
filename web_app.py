from pathlib import Path

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
from urllib.parse import quote

import bcrypt

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
from database import AdminTruth, ClaimCheckRecord, User, engine, init_db
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


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _session_record_label(request: Request) -> str:
    """Label stored on ClaimCheckRecord rows for the logged-in user."""
    raw = request.session.get("user_label")
    if raw:
        return str(raw).strip()[:100]
    uid = request.session.get("user_id")
    if uid and request.session.get("user_email"):
        return str(request.session["user_email"])[:100]
    return "guest"


def _template_ctx(request: Request, **extra) -> dict:
    ctx = {
        "request": request,
        "is_admin": _is_admin(request),
        "logged_in": bool(request.session.get("user_id")),
        "user_email": request.session.get("user_email") or "",
        "user_label": request.session.get("user_label") or "",
    }
    ctx.update(extra)
    return ctx


def _require_login_redirect(request: Request, next_path: str) -> RedirectResponse | None:
    if request.session.get("user_id"):
        return None
    safe = next_path if next_path.startswith("/") else "/chat"
    return RedirectResponse(url=f"/login?next={quote(safe, safe='')}", status_code=303)


def _require_user_api(request: Request) -> JSONResponse | None:
    if request.session.get("user_id"):
        return None
    return JSONResponse({"error": "Sign in required.", "detail": "Sign in required."}, status_code=401)


def _set_user_session(request: Request, user: User) -> None:
    label = (user.display_name or "").strip()[:100] or (user.email or "")[:100]
    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["user_label"] = label


def _clear_user_session(request: Request) -> None:
    for key in ("user_id", "user_email", "user_label"):
        request.session.pop(key, None)


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
    return templates.TemplateResponse("landing.html", _template_ctx(request))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/chat"):
    if request.session.get("user_id"):
        dest = next if next.startswith("/") else "/chat"
        return RedirectResponse(url=dest, status_code=303)
    safe_next = next if next.startswith("/") else "/chat"
    return templates.TemplateResponse(
        "login.html",
        _template_ctx(request, error="", next_url=safe_next),
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(default=""),
    password: str = Form(default=""),
    next: str = Form(default="/chat"),
):
    safe_next = next if next.startswith("/") else "/chat"
    err_ctx = lambda msg: _template_ctx(request, error=msg, next_url=safe_next)

    em = email.strip().lower()
    if not em or "@" not in em:
        return templates.TemplateResponse("login.html", err_ctx("Enter a valid email address."))
    if not password:
        return templates.TemplateResponse("login.html", err_ctx("Password is required."))

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == em)).first()
    if not user or not _verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", err_ctx("Invalid email or password."))

    _set_user_session(request, user)
    return RedirectResponse(url=safe_next, status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/chat", status_code=303)
    return templates.TemplateResponse("register.html", _template_ctx(request, error=""))


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(default=""),
    password: str = Form(default=""),
    display_name: str = Form(default=""),
):
    em = email.strip().lower()
    if not em or "@" not in em:
        return templates.TemplateResponse(
            "register.html",
            _template_ctx(request, error="Enter a valid email address."),
        )
    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            _template_ctx(request, error="Password must be at least 8 characters."),
        )

    display_clean = display_name.strip()[:100]

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == em)).first()
        if existing:
            return templates.TemplateResponse(
                "register.html",
                _template_ctx(request, error="An account with this email already exists."),
            )
        user = User(
            email=em,
            password_hash=_hash_password(password),
            display_name=display_clean,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    _set_user_session(request, user)
    return RedirectResponse(url="/chat", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    _clear_user_session(request)
    return RedirectResponse(url="/", status_code=303)


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    redir = _require_login_redirect(request, "/chat")
    if redir:
        return redir
    return templates.TemplateResponse("chat.html", _template_ctx(request))


@app.post("/api/chat")
async def api_chat(request: Request, body: ChatRequest):
    deny = _require_user_api(request)
    if deny:
        return deny
    services: AppServices = request.app.state.services
    user_label = _session_record_label(request)
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
    deny = _require_user_api(request)
    if deny:
        return deny
    services: AppServices = request.app.state.services
    user_label = _session_record_label(request)
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
    redir = _require_login_redirect(request, "/history")
    if redir:
        return redir
    user_label = _session_record_label(request)
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
        _template_ctx(request, records=records),
    )


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", _template_ctx(request))


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(
        "admin_login.html",
        _template_ctx(request, error="", admin_enabled=_admin_enabled()),
    )


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, password: str = Form(default="")):
    if not _admin_enabled():
        return templates.TemplateResponse(
            "admin_login.html",
            _template_ctx(
                request,
                error="ADMIN_PASSWORD is not configured on the server.",
                admin_enabled=False,
            ),
        )
    if password != _admin_password():
        return templates.TemplateResponse(
            "admin_login.html",
            _template_ctx(request, error="Invalid admin password.", admin_enabled=True),
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

    with Session(engine) as session:
        truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())
    return templates.TemplateResponse(
        "admin.html",
        _template_ctx(request, truths=truths, message="", error=""),
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

    claim = claim.strip()
    explanation = explanation.strip()
    if not claim or not explanation:
        with Session(engine) as session:
            truths = list(session.exec(select(AdminTruth).order_by(desc(AdminTruth.created_at))).all())
        return templates.TemplateResponse(
            "admin.html",
            _template_ctx(
                request,
                truths=truths,
                message="",
                error="Claim and explanation are required.",
            ),
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
        _template_ctx(
            request,
            truths=truths,
            message="Truth added and index refreshed.",
            error="",
        ),
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
