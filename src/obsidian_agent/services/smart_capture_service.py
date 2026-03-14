"""Smart error capture orchestration."""

from __future__ import annotations

from obsidian_agent.domain.schemas import ErrorCaptureRequest, SmartErrorCaptureResponse
from obsidian_agent.services.error_extractor_service import ErrorExtractorService
from obsidian_agent.services.node_writer_service import NodeWriterService
from obsidian_agent.services.weakness_diagnoser_service import WeaknessDiagnoserService


class SmartCaptureService:
    """Turn an error submission into structured smart nodes."""

    def __init__(
        self,
        error_extractor: ErrorExtractorService,
        weakness_diagnoser: WeaknessDiagnoserService,
        node_writer: NodeWriterService,
    ) -> None:
        self.error_extractor = error_extractor
        self.weakness_diagnoser = weakness_diagnoser
        self.node_writer = node_writer

    async def capture_error(self, payload: ErrorCaptureRequest) -> SmartErrorCaptureResponse:
        error = await self.error_extractor.extract(payload)
        weaknesses = await self.weakness_diagnoser.diagnose(error)
        node, related_nodes, action_preview, stored_edges = await self.node_writer.write_error_bundle(
            payload,
            error,
            weaknesses,
        )
        return SmartErrorCaptureResponse(
            error=error,
            weaknesses=weaknesses,
            node=node,
            related_nodes=related_nodes,
            action_preview=action_preview,
            stored_edges=stored_edges,
            telemetry={
                "error_extractor": self.error_extractor.last_telemetry,
                "weakness_count": len(weaknesses),
                "related_node_count": len(related_nodes),
            },
        )
