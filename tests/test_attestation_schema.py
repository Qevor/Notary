from notary.models.schemas import VerdictOutcome, WitnessVerdict


def test_witness_verdict_schema_accepts_graded_outcome() -> None:
    verdict = WitnessVerdict(
        obligation_id="obl_test",
        outcome=VerdictOutcome.PARTIAL_RELEASE,
        release_pct=65,
        confidence=0.78,
        deficiency="One deliverable element was incomplete.",
        reasoning_trace="NOTARY TESTIMONY",
    )
    assert verdict.release_pct == 65
