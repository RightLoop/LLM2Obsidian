"""Risk and integration policies."""

from obsidian_agent.domain.enums import NoteKind, ProposalType, RiskLevel


def classify_risk(proposal_type: ProposalType, target_kind: NoteKind | None = None) -> RiskLevel:
    """Return the risk level for a proposal."""

    if proposal_type in {ProposalType.NEW_NOTE, ProposalType.WEEKLY_DIGEST}:
        return RiskLevel.LOW

    if proposal_type in {ProposalType.APPEND_CANDIDATE, ProposalType.FRONTMATTER_UPDATE}:
        return RiskLevel.MEDIUM

    if proposal_type in {ProposalType.MERGE_CANDIDATE, ProposalType.REVIEW_ONLY}:
        return RiskLevel.HIGH

    if target_kind == NoteKind.EVERGREEN:
        return RiskLevel.HIGH

    return RiskLevel.MEDIUM


def can_auto_apply(risk_level: RiskLevel | str) -> bool:
    """Only low and medium risk items can be auto-applied after approval."""

    value = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
    return value in {RiskLevel.LOW.value, RiskLevel.MEDIUM.value}
