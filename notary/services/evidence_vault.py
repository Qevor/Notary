from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import EvidenceAccessGrant, PrivacyMode, new_id


@dataclass(slots=True)
class EvidenceVault:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def store_text(self, text: str, privacy_mode: PrivacyMode) -> dict[str, str]:
        evidence_id = new_id("ev")
        raw_hash = sha256_hex(text)
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        path = self.root / f"{evidence_id}.b64"
        path.write_text(encoded, encoding="utf-8")
        return {
            "evidenceId": evidence_id,
            "rawHash": raw_hash,
            "encryptedUri": str(path),
            "privacyMode": privacy_mode.value,
        }

    def read_text(self, encrypted_uri: str) -> str:
        encoded = Path(encrypted_uri).read_text(encoding="utf-8")
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8")

    def create_access_grant(
        self, evidence_id: str, grantee: str, purpose: str, level: str
    ) -> EvidenceAccessGrant:
        return EvidenceAccessGrant(
            evidence_id=evidence_id,
            grantee=grantee,
            purpose=purpose,
            disclosure_level=level,
        )

