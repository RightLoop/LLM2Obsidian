"""Provider routing for smart tasks."""

from __future__ import annotations

from obsidian_agent.services.llm_service import LLMService


class RoutingPolicyService:
    """Choose the most appropriate model service for each smart task."""

    def __init__(self, primary_llm_service: LLMService, local_llm_service: LLMService | None = None) -> None:
        self.primary_llm_service = primary_llm_service
        self.local_llm_service = local_llm_service

    def for_structured_task(self) -> LLMService:
        if self.local_llm_service and self.local_llm_service.client is not None:
            return self.local_llm_service
        return self.primary_llm_service

    def for_teaching_task(self) -> LLMService:
        if self.primary_llm_service and self.primary_llm_service.client is not None:
            return self.primary_llm_service
        if self.local_llm_service and self.local_llm_service.client is not None:
            return self.local_llm_service
        return self.primary_llm_service
