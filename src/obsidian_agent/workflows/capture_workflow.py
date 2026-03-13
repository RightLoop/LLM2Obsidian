"""Capture workflow."""

from obsidian_agent.domain.schemas import CaptureInput
from obsidian_agent.services.capture_service import CaptureService
from obsidian_agent.services.normalize_service import NormalizeService


class CaptureWorkflow:
    """Normalize and capture new content."""

    def __init__(self, normalize_service: NormalizeService, capture_service: CaptureService) -> None:
        self.normalize_service = normalize_service
        self.capture_service = capture_service

    async def run(self, payload: CaptureInput) -> dict[str, object]:
        normalized = await self.normalize_service.normalize(payload)
        return await self.capture_service.capture(normalized)
