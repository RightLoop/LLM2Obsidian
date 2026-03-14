"""Capture routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.enums import SourceType
from obsidian_agent.domain.schemas import (
    CaptureClipboardRequest,
    CaptureInput,
    CapturePdfTextRequest,
    CaptureTextRequest,
    CaptureUrlRequest,
)
from obsidian_agent.integrations.html_fetcher import UnsafeUrlError, fetch_url_text

router = APIRouter(prefix="/capture", tags=["capture"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.post("/text")
async def capture_text(request: CaptureTextRequest, container: ContainerDep) -> dict[str, object]:
    payload = CaptureInput(
        source_type=SourceType.TEXT,
        text=request.text,
        title=request.title,
        source_ref=request.source_ref,
    )
    return await container.capture_workflow.run(payload)


@router.post("/url")
async def capture_url(request: CaptureUrlRequest, container: ContainerDep) -> dict[str, object]:
    try:
        title, text = await fetch_url_text(
            request.url,
            timeout_seconds=container.settings.http_timeout_seconds,
        )
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    payload = CaptureInput(
        source_type=SourceType.URL,
        text=text,
        title=request.title_hint or title,
        source_ref=request.url,
    )
    return await container.capture_workflow.run(payload)


@router.post("/clipboard")
async def capture_clipboard(
    request: CaptureClipboardRequest, container: ContainerDep
) -> dict[str, object]:
    payload = CaptureInput(source_type=SourceType.CLIPBOARD, text=request.text)
    return await container.capture_workflow.run(payload)


@router.post("/pdf-text")
async def capture_pdf_text(request: CapturePdfTextRequest, container: ContainerDep) -> dict[str, object]:
    payload = CaptureInput(
        source_type=SourceType.PDF,
        text=request.text,
        title=request.title,
        source_ref=request.source_ref,
    )
    return await container.capture_workflow.run(payload)
