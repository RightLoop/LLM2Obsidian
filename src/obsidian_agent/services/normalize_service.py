"""Normalization helpers."""

from obsidian_agent.domain.enums import SourceType
from obsidian_agent.domain.schemas import CaptureInput
from obsidian_agent.integrations.clipboard_ingest import normalize_clipboard_text
from obsidian_agent.integrations.pdf_ingest import extract_pdf_text


class NormalizeService:
    """Normalize raw external inputs before capture."""

    async def normalize(self, payload: CaptureInput) -> CaptureInput:
        if payload.source_type == SourceType.CLIPBOARD:
            payload.text = normalize_clipboard_text(payload.text)
        if payload.source_type == SourceType.PDF:
            payload.text = extract_pdf_text(payload.text)
        return payload
