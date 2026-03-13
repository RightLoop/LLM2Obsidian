from obsidian_agent.domain.enums import ProposalType, RiskLevel
from obsidian_agent.domain.policies import can_auto_apply, classify_risk


def test_classify_risk_levels() -> None:
    assert classify_risk(ProposalType.NEW_NOTE) == RiskLevel.LOW
    assert classify_risk(ProposalType.APPEND_CANDIDATE) == RiskLevel.MEDIUM
    assert classify_risk(ProposalType.MERGE_CANDIDATE) == RiskLevel.HIGH


def test_can_auto_apply() -> None:
    assert can_auto_apply(RiskLevel.LOW) is True
    assert can_auto_apply(RiskLevel.HIGH) is False
