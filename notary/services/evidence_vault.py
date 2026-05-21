from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from notary.crypto.hashing import sha256_hex
from notary.models.schemas import DisclosureLevel, EvidenceAccessGrant, PrivacyMode, new_id


@dataclass(slots=True)
class EvidenceVault:
    root: Path
    passphrase: str | None = None
    _key_file: Path = field(init=False, repr=False)
    _passphrase: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "_key_file", self.root / ".vault.key")
        object.__setattr__(self, "_passphrase", self.passphrase or self._load_or_create_passphrase())

    def _load_or_create_passphrase(self) -> str:
        if self._key_file.exists():
            return self._key_file.read_text(encoding="utf-8").strip()
        secret = secrets.token_hex(32)
        self._key_file.write_text(secret, encoding="utf-8")
        os.chmod(self._key_file, 0o600)
        return secret

    def _encrypt_bytes(self, payload: bytes, destination: Path) -> None:
        if shutil.which("openssl") is None:
            destination.write_bytes(b"NOTARYXOR1" + self._xor_stream(payload))
            return
        proc = subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-256-cbc",
                "-pbkdf2",
                "-salt",
                "-pass",
                f"pass:{self._passphrase}",
                "-out",
                str(destination),
            ],
            input=payload,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"openssl encryption failed: {stderr or 'unknown error'}")

    def _decrypt_bytes(self, encrypted_uri: str) -> bytes:
        raw = Path(encrypted_uri).read_bytes()
        if raw.startswith(b"NOTARYXOR1"):
            return self._xor_stream(raw.removeprefix(b"NOTARYXOR1"))
        proc = subprocess.run(
            [
                "openssl",
                "enc",
                "-d",
                "-aes-256-cbc",
                "-pbkdf2",
                "-pass",
                f"pass:{self._passphrase}",
                "-in",
                encrypted_uri,
            ],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"openssl decryption failed: {stderr or 'unknown error'}")
        return proc.stdout

    def _xor_stream(self, payload: bytes) -> bytes:
        key = self._passphrase.encode("utf-8")
        output = bytearray()
        counter = 0
        while len(output) < len(payload):
            output.extend(sha256(key + counter.to_bytes(8, "big")).digest())
            counter += 1
        return bytes(byte ^ mask for byte, mask in zip(payload, output, strict=False))

    def store_bytes(self, payload: bytes, *, prefix: str, suffix: str, privacy_mode: PrivacyMode) -> dict[str, str]:
        evidence_id = new_id(prefix)
        raw_hash = sha256_hex(payload)
        path = self.root / f"{evidence_id}{suffix}.enc"
        self._encrypt_bytes(payload, path)
        return {
            "evidenceId": evidence_id,
            "rawHash": raw_hash,
            "encryptedUri": str(path),
            "privacyMode": privacy_mode.value,
            "cipher": "aes-256-cbc" if shutil.which("openssl") else "notary-local-xor",
        }

    def store_text(self, text: str, privacy_mode: PrivacyMode) -> dict[str, str]:
        return self.store_bytes(
            text.encode("utf-8"),
            prefix="ev",
            suffix=".txt",
            privacy_mode=privacy_mode,
        )

    def store_file(self, file_path: Path, privacy_mode: PrivacyMode) -> dict[str, str]:
        return self.store_bytes(
            file_path.read_bytes(),
            prefix="file",
            suffix=file_path.suffix or ".bin",
            privacy_mode=privacy_mode,
        )

    def read_text(self, encrypted_uri: str) -> str:
        return self._decrypt_bytes(encrypted_uri).decode("utf-8")

    def create_access_grant(
        self,
        evidence_id: str,
        grantee: str,
        purpose: str,
        level: DisclosureLevel | str,
    ) -> EvidenceAccessGrant:
        disclosure_level = level if isinstance(level, DisclosureLevel) else DisclosureLevel(level)
        return EvidenceAccessGrant(
            evidence_id=evidence_id,
            grantee=grantee,
            purpose=purpose,
            disclosure_level=disclosure_level,
        )
