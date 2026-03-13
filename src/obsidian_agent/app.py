"""FastAPI application factory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from obsidian_agent.config import Settings, get_settings
from obsidian_agent.integrations.deepseek_client import DeepSeekChatClient
from obsidian_agent.integrations.obsidian_rest_client import ObsidianRestClient
from obsidian_agent.integrations.openai_client import OpenAIResponsesClient
from obsidian_agent.logging import configure_logging, trace_middleware
from obsidian_agent.services.capture_service import CaptureService
from obsidian_agent.services.embeddings_service import EmbeddingsService
from obsidian_agent.services.indexing_service import IndexingService
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.services.maintenance_service import MaintenanceService
from obsidian_agent.services.normalize_service import NormalizeService
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.services.retrieval_service import RetrievalService
from obsidian_agent.services.review_service import ReviewService
from obsidian_agent.services.synthesis_service import SynthesisService
from obsidian_agent.storage.db import create_session_factory
from obsidian_agent.storage.vector_store import VectorStore
from obsidian_agent.workflows.capture_workflow import CaptureWorkflow
from obsidian_agent.workflows.link_workflow import LinkWorkflow
from obsidian_agent.workflows.maintenance_workflow import MaintenanceWorkflow
from obsidian_agent.workflows.synthesis_workflow import SynthesisWorkflow


@dataclass
class AppContainer:
    """Shared application services."""

    settings: Settings
    session_factory: sessionmaker
    obsidian_service: ObsidianService
    llm_service: LLMService
    capture_workflow: CaptureWorkflow
    retrieval_service: RetrievalService
    review_service: ReviewService
    synthesis_service: SynthesisService
    synthesis_workflow: SynthesisWorkflow
    indexing_service: IndexingService
    maintenance_service: MaintenanceService
    maintenance_workflow: MaintenanceWorkflow
    link_workflow: LinkWorkflow


def _template_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "prompts" / "tasks" / name


def _ui_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "ui" / name


def build_container(settings: Settings | None = None) -> AppContainer:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    session_factory = create_session_factory(settings.sqlite_path)
    rest_client = (
        ObsidianRestClient(
            settings.obsidian_api_url,
            settings.obsidian_api_key,
            verify_ssl=settings.obsidian_verify_ssl,
            timeout_seconds=settings.http_timeout_seconds,
            retry_attempts=settings.http_retry_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        )
        if settings.obsidian_api_url
        else None
    )
    obsidian_service = ObsidianService(settings, rest_client)
    llm_client = None
    provider = settings.llm_provider.lower()
    if provider in {"auto", "deepseek"} and settings.deepseek_api_key:
        llm_client = DeepSeekChatClient(
            settings.deepseek_api_key,
            settings.deepseek_base_url,
            settings.deepseek_model,
            timeout_seconds=settings.http_timeout_seconds,
            retry_attempts=settings.http_retry_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        )
    elif provider in {"auto", "openai"} and settings.openai_api_key:
        llm_client = OpenAIResponsesClient(
            settings.openai_api_key,
            settings.openai_base_url,
            settings.openai_model,
            timeout_seconds=settings.http_timeout_seconds,
            retry_attempts=settings.http_retry_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        )
    llm_service = LLMService(llm_client)
    embeddings_service = EmbeddingsService()
    vector_store = VectorStore(settings.vector_store_path)
    retrieval_service = RetrievalService(session_factory, obsidian_service, embeddings_service, vector_store)
    review_service = ReviewService(
        session_factory=session_factory,
        obsidian_service=obsidian_service,
        template_path=_template_path("review_note.md.tmpl"),
    )
    synthesis_service = SynthesisService(llm_service)
    synthesis_workflow = SynthesisWorkflow(synthesis_service, review_service)
    capture_service = CaptureService(
        session_factory=session_factory,
        obsidian_service=obsidian_service,
        llm_service=llm_service,
        inbox_template_path=_template_path("inbox_note.md.tmpl"),
    )
    capture_workflow = CaptureWorkflow(NormalizeService(), capture_service)
    indexing_service = IndexingService(session_factory, obsidian_service, embeddings_service, vector_store)
    maintenance_service = MaintenanceService(
        session_factory=session_factory,
        obsidian_service=obsidian_service,
        llm_service=llm_service,
        weekly_digest_template_path=_template_path("weekly_digest.md.tmpl"),
    )
    maintenance_workflow = MaintenanceWorkflow(maintenance_service)
    link_workflow = LinkWorkflow(retrieval_service)
    return AppContainer(
        settings=settings,
        session_factory=session_factory,
        obsidian_service=obsidian_service,
        llm_service=llm_service,
        capture_workflow=capture_workflow,
        retrieval_service=retrieval_service,
        review_service=review_service,
        synthesis_service=synthesis_service,
        synthesis_workflow=synthesis_workflow,
        indexing_service=indexing_service,
        maintenance_service=maintenance_service,
        maintenance_workflow=maintenance_workflow,
        link_workflow=link_workflow,
    )


def get_container(request: Request) -> AppContainer:
    """Resolve the service container."""

    return request.app.state.container


def create_app() -> FastAPI:
    """Create the FastAPI app."""

    from obsidian_agent.api.routes_capture import router as capture_router
    from obsidian_agent.api.routes_maintenance import router as maintenance_router
    from obsidian_agent.api.routes_review import router as review_router
    from obsidian_agent.api.routes_search import router as search_router
    from obsidian_agent.api.routes_ui import router as ui_router

    app = FastAPI(title="LLM2Obsidian")
    app.middleware("http")(trace_middleware)
    app.state.container = build_container()
    app.mount("/ui/assets", StaticFiles(directory=_ui_path("")), name="ui-assets")
    app.include_router(ui_router)
    app.include_router(capture_router)
    app.include_router(search_router)
    app.include_router(review_router)
    app.include_router(maintenance_router)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
