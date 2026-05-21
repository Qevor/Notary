from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notary.models.schemas import EvidenceSource, NotaryState, Observation, PrivacyMode
from notary.swarm.notary_swarm import run_notary_cycle


async def main() -> None:
    observation = Observation(
        source=EvidenceSource(kind="demo_transcript", uri="demo://work-call"),
        summary="Client approved the final design and requested payment release.",
        raw_text="Client: The final design is approved and the work is complete. Release payment.",
        privacy_mode=PrivacyMode.PROTECTED,
        confidence=0.82,
    )
    state = await run_notary_cycle(NotaryState(observations=[observation]))
    print(json.dumps(state.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
