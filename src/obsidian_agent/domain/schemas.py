"""Pydantic schemas used by the API and services."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from obsidian_agent.domain.enums import (
    KnowledgeNodeType,
    KnowledgeRelationType,
    NoteKind,
    NoteStatus,
    ProposalType,
    ReviewState,
    RiskLevel,
    SourceType,
)


class FrontmatterSchema(BaseModel):
    """Frontmatter contract for generated notes."""

    id: str
    kind: NoteKind
    status: NoteStatus
    source_type: SourceType
    source_ref: str = ""
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    generated_by: str = "obsidian-agent"
    review_required: bool = True
    review_after: datetime | None = None


class CaptureTextRequest(BaseModel):
    title: str | None = None
    text: str
    source_ref: str = ""
    tags: list[str] = Field(default_factory=list)


class CaptureUrlRequest(BaseModel):
    url: str
    title_hint: str | None = None


class CaptureClipboardRequest(BaseModel):
    text: str


class CapturePdfTextRequest(BaseModel):
    title: str | None = None
    text: str
    source_ref: str = ""


class CaptureInput(BaseModel):
    source_type: SourceType
    text: str
    title: str | None = None
    source_ref: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class RelatedNoteCandidate(BaseModel):
    path: str
    reason: str
    score: float


class NormalizedCapture(BaseModel):
    title: str
    summary: str
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    related_candidates: list[RelatedNoteCandidate] = Field(default_factory=list)
    decision: ProposalType = ProposalType.NEW_NOTE
    confidence: float = 0.5
    conflicts: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    raw_excerpt: str = ""


class NoteRecordSchema(BaseModel):
    id: int | None = None
    vault_path: str
    title: str
    kind: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_type: str | None = None
    source_ref: str | None = None
    content_hash: str | None = None
    word_count: int = 0
    indexed_at: datetime | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[RelatedNoteCandidate]


class ReviewProposal(BaseModel):
    proposal_type: ProposalType
    risk_level: RiskLevel
    title: str
    source_note_path: str
    target_note_path: str | None = None
    rationale: str
    suggested_patch: str
    related_links: list[str] = Field(default_factory=list)


class GenerateReviewRequest(BaseModel):
    note_path: str
    top_k: int = 5


class ReviewItemSchema(BaseModel):
    id: int | None = None
    source_note_id: int | None = None
    target_note_id: int | None = None
    source_note_path: str | None = None
    target_note_path: str | None = None
    proposal_type: ProposalType
    suggested_patch: str | None = None
    proposal_path: str
    state: ReviewState
    risk_level: RiskLevel
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WeeklyDigestRequest(BaseModel):
    week_key: str


class MaintenanceFinding(BaseModel):
    path: str
    reason: str
    score: float = 0.0


class ActionPreview(BaseModel):
    dry_run: bool
    action: str
    target_path: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorCaptureRequest(BaseModel):
    title: str | None = None
    prompt: str = Field(min_length=10)
    code: str = ""
    user_analysis: str = ""
    language: str = "c"
    source_ref: str = ""


class ErrorObject(BaseModel):
    title: str
    language: str = "c"
    error_signature: str
    summary: str
    root_cause: str
    incorrect_assumption: str
    evidence: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class WeaknessObject(BaseModel):
    name: str
    summary: str
    gap_type: str
    recommended_practice: str
    related_concepts: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class KnowledgeNodeSchema(BaseModel):
    id: int | None = None
    node_key: str
    node_type: KnowledgeNodeType
    title: str
    summary: str
    note_path: str | None = None
    source_note_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class KnowledgeEdgeSchema(BaseModel):
    id: int | None = None
    from_node_key: str
    to_node_key: str
    relation_type: KnowledgeRelationType
    reason: str
    confidence: float = 0.5


class RelationPack(BaseModel):
    anchor: KnowledgeNodeSchema
    related_nodes: list[KnowledgeNodeSchema] = Field(default_factory=list)
    edges: list[KnowledgeEdgeSchema] = Field(default_factory=list)
    summary: str = ""


class SmartErrorCaptureResponse(BaseModel):
    error: ErrorObject
    weaknesses: list[WeaknessObject] = Field(default_factory=list)
    node: KnowledgeNodeSchema
    related_nodes: list[KnowledgeNodeSchema] = Field(default_factory=list)
    action_preview: ActionPreview | None = None
    stored_edges: int = 0


class NodePackRequest(BaseModel):
    node_key: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)


class SmartNodePackResponse(BaseModel):
    pack: RelationPack
    stored_edges: int = 0


class RelatedNodesRequest(BaseModel):
    node_key: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)


class TeachingPackRequest(BaseModel):
    node_key: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)


class TeachingSection(BaseModel):
    heading: str
    body: str


class TeachingPackResponse(BaseModel):
    pack: RelationPack
    title: str
    overview: str
    sections: list[TeachingSection] = Field(default_factory=list)
    drills: list[str] = Field(default_factory=list)
    markdown: str


class SmartRelinkRequest(BaseModel):
    node_key: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)
    create_review: bool = True
    dry_run: bool = True


class SmartRelinkResponse(BaseModel):
    pack: RelationPack
    related_section_markdown: str
    stored_edges: int = 0
    review_id: int | None = None
    proposal_path: str | None = None
    action_preview: ActionPreview | None = None
