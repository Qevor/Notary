import pytest

from notary.models.schemas import EvidenceSource, NotaryState, Observation, PrivacyMode
from notary.swarm.notary_swarm import run_notary_cycle


@pytest.mark.asyncio
async def test_swarm_cycle_creates_attestation_and_payment_trigger() -> None:
    observation = Observation(
        source=EvidenceSource(kind="demo"),
        summary="Client approved final work and requested release.",
        raw_text="The final work is approved. Please release the payment.",
        privacy_mode=PrivacyMode.PROTECTED,
        confidence=0.82,
    )
    result = await run_notary_cycle(NotaryState(observations=[observation]))
    assert result.attestations
    assert result.predictions
    assert result.payment_triggers
    assert result.karma is not None

