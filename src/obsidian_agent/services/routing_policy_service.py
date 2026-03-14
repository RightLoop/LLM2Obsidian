"""Provider routing for smart tasks."""

from __future__ import annotations

import logging

from obsidian_agent.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class RoutingPolicyService:
    """Choose the most appropriate model service for each smart task."""

    def __init__(self, primary_llm_service: LLMService, local_llm_service: LLMService | None = None) -> None:
        self.primary_llm_service = primary_llm_service
        self.local_llm_service = local_llm_service

    def for_structured_task(self, task_name: str = "structured") -> LLMService:
        if self.local_llm_service and self.local_llm_service.client is not None:
            service = self.local_llm_service
        else:
            service = self.primary_llm_service
        logger.info("smart_route task=%s provider=%s model=%s", task_name, service.describe()["provider"], service.describe()["model"])
        return service

    def for_teaching_task(self, task_name: str = "teaching", delivery_mode: str = "auto") -> tuple[LLMService, str]:
        requested = delivery_mode.lower().strip() or "auto"
        primary_available = self.primary_llm_service.client is not None
        local_available = self.local_llm_service is not None and self.local_llm_service.client is not None
        service = self.primary_llm_service
        resolved = "offline"

        if requested == "local":
            if local_available:
                service = self.local_llm_service
                resolved = "local"
            elif primary_available:
                service = self.primary_llm_service
                resolved = "remote-fallback"
        elif requested == "remote":
            if primary_available:
                service = self.primary_llm_service
                resolved = "remote"
            elif local_available:
                service = self.local_llm_service
                resolved = "local-fallback"
        else:
            if primary_available:
                service = self.primary_llm_service
                resolved = "remote"
            elif local_available:
                service = self.local_llm_service
                resolved = "local"

        logger.info(
            "smart_route task=%s requested=%s resolved=%s provider=%s model=%s",
            task_name,
            requested,
            resolved,
            service.describe()["provider"],
            service.describe()["model"],
        )
        return service, resolved
