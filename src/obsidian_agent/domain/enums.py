"""Shared enums."""

from enum import StrEnum


class NoteKind(StrEnum):
    INBOX = "inbox"
    LITERATURE = "literature"
    PROJECT = "project"
    EVERGREEN = "evergreen"
    FLEETING = "fleeting"
    ENTITY = "entity"
    REVIEW = "review"
    DIGEST = "digest"


class NoteStatus(StrEnum):
    INBOX = "inbox"
    DRAFT = "draft"
    REVIEW = "review"
    STABLE = "stable"
    ARCHIVED = "archived"


class SourceType(StrEnum):
    URL = "url"
    PDF = "pdf"
    CHAT = "chat"
    CLIPBOARD = "clipboard"
    MANUAL = "manual"
    TEXT = "text"


class ProposalType(StrEnum):
    NEW_NOTE = "new_note"
    APPEND_CANDIDATE = "append_candidate"
    MERGE_CANDIDATE = "merge_candidate"
    REVIEW_ONLY = "review_only"
    FRONTMATTER_UPDATE = "frontmatter_update"
    WEEKLY_DIGEST = "weekly_digest"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LinkType(StrEnum):
    EXPLICIT = "explicit"
    SUGGESTED = "suggested"
    SEMANTIC = "semantic"
    ENTITY_MATCH = "entity_match"


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReviewState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
