"""Generate teaching-oriented outputs from relation packs."""

from __future__ import annotations

import logging

from obsidian_agent.domain.schemas import (
    RelationPack,
    TeachingPackRequest,
    TeachingPackResponse,
    TeachingSection,
)
from obsidian_agent.services.routing_policy_service import RoutingPolicyService
from obsidian_agent.services.smart_node_pack_service import SmartNodePackService

logger = logging.getLogger(__name__)


class TeachingPlannerService:
    """Turn a relation pack into a teaching pack preview."""

    def __init__(
        self,
        smart_node_pack_service: SmartNodePackService,
        routing_policy: RoutingPolicyService,
    ) -> None:
        self.smart_node_pack_service = smart_node_pack_service
        self.routing_policy = routing_policy
        self.last_telemetry: dict[str, object] = {}

    async def build_teaching_pack(self, request: TeachingPackRequest) -> TeachingPackResponse:
        pack_response = await self.smart_node_pack_service.build_node_pack(
            node_key=request.node_key,
            top_k=request.top_k,
        )
        pack = pack_response.pack
        payload = await self._plan_from_model(pack)
        if payload is None:
            payload = self._fallback_plan(pack)
        markdown = self._render_markdown(
            title=payload["title"],
            overview=payload["overview"],
            sections=payload["sections"],
            drills=payload["drills"],
        )
        return TeachingPackResponse(
            pack=pack,
            title=payload["title"],
            overview=payload["overview"],
            sections=payload["sections"],
            drills=payload["drills"],
            markdown=markdown,
            telemetry={
                "planner": self.last_telemetry,
                "pack": pack_response.telemetry,
            },
        )

    async def _plan_from_model(self, pack: RelationPack) -> dict[str, object] | None:
        llm_service = self.routing_policy.for_teaching_task("teaching_planner")
        raw = await llm_service.run_structured_task(
            instructions=(
                "Return JSON with keys: title, overview, sections, drills. "
                "sections must be a list of objects with heading and body. "
                "drills must be a list of short practice prompts. "
                "Focus on teaching the anchor concept using the related nodes and relations."
            ),
            input_text="\n".join(
                [
                    f"Anchor: {pack.anchor.title}",
                    f"Anchor summary: {pack.anchor.summary}",
                    f"Relation summary: {pack.summary}",
                    "Related nodes:",
                    *[f"- {node.title}: {node.summary}" for node in pack.related_nodes],
                    "Edges:",
                    *[
                        f"- {edge.relation_type.value} -> {edge.to_node_key}: {edge.reason}"
                        for edge in pack.edges
                    ],
                ]
            ),
        )
        self.last_telemetry = llm_service.pop_telemetry()
        if self.last_telemetry:
            logger.info("smart_telemetry task=teaching_planner telemetry=%s", self.last_telemetry)
        if not isinstance(raw, dict):
            return None
        title = str(raw.get("title") or "").strip()
        overview = str(raw.get("overview") or "").strip()
        sections_raw = raw.get("sections")
        drills_raw = raw.get("drills")
        sections: list[TeachingSection] = []
        if isinstance(sections_raw, list):
            for item in sections_raw:
                if not isinstance(item, dict):
                    continue
                heading = str(item.get("heading") or "").strip()
                body = str(item.get("body") or "").strip()
                if heading and body:
                    sections.append(TeachingSection(heading=heading, body=body))
        drills: list[str] = []
        if isinstance(drills_raw, list):
            drills = [str(item).strip() for item in drills_raw if str(item).strip()]
        if not title or not overview or not sections:
            return None
        return {
            "title": title,
            "overview": overview,
            "sections": sections,
            "drills": drills[:5],
        }

    def _fallback_plan(self, pack: RelationPack) -> dict[str, object]:
        related_titles = ", ".join(node.title for node in pack.related_nodes[:3]) or "nearby concepts"
        sections = [
            TeachingSection(
                heading="What To Remember",
                body=f"{pack.anchor.title} should be understood in terms of {pack.anchor.summary}",
            ),
            TeachingSection(
                heading="How It Connects",
                body=f"This topic is most often reinforced or contrasted with {related_titles}.",
            ),
        ]
        if pack.edges:
            sections.append(
                TeachingSection(
                    heading="Common Failure Mode",
                    body=pack.edges[0].reason,
                )
            )
        drills = [
            f"Explain {pack.anchor.title} in your own words.",
            f"Write one C example that avoids the mistake behind {pack.anchor.title}.",
        ]
        return {
            "title": f"Teaching Pack: {pack.anchor.title}",
            "overview": pack.summary or pack.anchor.summary,
            "sections": sections,
            "drills": drills,
        }

    def _render_markdown(
        self,
        title: str,
        overview: str,
        sections: list[TeachingSection],
        drills: list[str],
    ) -> str:
        lines = [f"# {title}", "", "## Overview", overview]
        for section in sections:
            lines.extend(["", f"## {section.heading}", section.body])
        lines.extend(["", "## Practice Drills"])
        if drills:
            lines.extend(f"- {item}" for item in drills)
        else:
            lines.append("- Review one fresh example and explain why it works.")
        return "\n".join(lines).strip() + "\n"
