from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from pydantic import BaseModel

from app.agent import run_agent
from app.agent.model_catalog import catalog_with_context, check_model
from app.agent.tools import TOOL_LABELS, TOOL_REGISTRY
from app.config import get_settings
from app.crud import list_hcp_profiles, save_interaction, seed_hcp_profiles
from app.db import Base, SessionLocal, engine, get_db
from app.models import HCPProfile, Interaction
from app.schemas import (
    AudioTranscriptionResponse,
    ChatRequest,
    ChatResponse,
    HCPProfileOut,
    InteractionDraft,
    InteractionOut,
)
from app.speech import SpeechConfigurationError, SpeechError, SpeechRateLimitError, transcribe_audio


logger = logging.getLogger(__name__)
database_ready = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    global database_ready
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_hcp_profiles(db)
        finally:
            db.close()
        database_ready = True
    except SQLAlchemyError as exc:
        database_ready = False
        logger.warning("Database unavailable at startup; AI and voice routes remain active: %s", exc)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "service": settings.app_name, "database_ready": database_ready}


@app.get(f"{settings.api_prefix}/tools")
def tools() -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "label": TOOL_LABELS[name],
            "description": tool.description or "",
        }
        for name, tool in TOOL_REGISTRY.items()
    ]


@app.get(f"{settings.api_prefix}/draft", response_model=InteractionDraft)
def get_empty_draft() -> InteractionDraft:
    return InteractionDraft()


@app.get(f"{settings.api_prefix}/hcps", response_model=list[HCPProfileOut])
def get_hcps(db: Session = Depends(get_db)) -> list[HCPProfile]:
    if not database_ready:
        raise HTTPException(status_code=503, detail="The SQL database is currently unavailable.")
    return list_hcp_profiles(db)


@app.post(f"{settings.api_prefix}/agent/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return run_agent(
        request.message,
        request.current_draft,
        request.preferences,
        model_override=request.planner_model,
    )


@app.post(f"{settings.api_prefix}/audio/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_voice(file: UploadFile = File(...)) -> dict[str, str]:
    data = await file.read(settings.voice_max_upload_bytes + 1)
    try:
        return transcribe_audio(file.filename or "voice-note.webm", file.content_type, data)
    except ValueError as exc:
        status_code = 413 if "20 MB" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except SpeechConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SpeechRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except SpeechError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/models")
def models() -> dict:
    """Model catalog + config context for the Developer settings panel."""
    return catalog_with_context()


class ModelCheckRequest(BaseModel):
    model_ids: list[str] | None = None


@app.post(f"{settings.api_prefix}/models/check")
def models_check(payload: ModelCheckRequest) -> dict:
    """Live status probe: pings each requested model with a minimal Groq call."""
    from app.agent.model_catalog import GROQ_MODEL_CATALOG

    ids = payload.model_ids or [item["id"] for item in GROQ_MODEL_CATALOG]
    return {"results": [check_model(model_id) for model_id in ids]}


@app.post(f"{settings.api_prefix}/interactions", response_model=InteractionOut)
def create_interaction(
    draft: InteractionDraft,
    db: Session = Depends(get_db),
) -> Interaction:
    if not database_ready:
        raise HTTPException(status_code=503, detail="The SQL database is currently unavailable.")
    return save_interaction(db, draft)
