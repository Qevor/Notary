from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notary.models.schemas import PrivacyMode, new_id


@dataclass(slots=True)
class SocialPublisher:
    demo_mode: bool = True

    async def publish(self, message: str, privacy_mode: PrivacyMode) -> dict[str, Any]:
        if privacy_mode != PrivacyMode.PUBLIC:
            return {"status": "skipped", "reason": "privacy_mode_not_public"}
        return {"status": "published", "postId": new_id("post"), "message": message, "demo": True}

