from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel

from notary.models.schemas import PrivacyMode


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _optional_str(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


class Settings(BaseModel):
    notary_env: str = "development"
    notary_demo_mode: bool = True
    notary_default_privacy_mode: PrivacyMode = PrivacyMode.PROTECTED

    validator_private_key: str | None = None
    validator_eip712_name: str = "NOTARY"
    validator_eip712_version: str = "1"

    arc_demo_mode: bool = True
    arc_rpc_url: str | None = None
    arc_chain_id: int | None = None
    arc_cli_path: str = "arc"
    arc_operator_private_key: str | None = None
    arc_notary_identity_registry: str | None = None
    arc_attestation_registry: str | None = None
    arc_karma_registry: str | None = None
    arc_validation_registry: str | None = None
    arc_governance: str | None = None

    qevorpay_demo_mode: bool = True
    qevorpay_api_base_url: str | None = None
    qevorpay_api_key: str | None = None
    qevorpay_webhook_secret: str | None = None

    speedmatic_demo_mode: bool = True
    speedmatic_api_base_url: str | None = None
    speedmatic_api_key: str | None = None

    evidence_vault_local_dir: Path = Path(".notary_vault")
    evidence_vault_passphrase: str | None = None
    notary_db_path: Path = Path(".notary/notary.sqlite3")

    @classmethod
    def from_env(cls) -> "Settings":
        chain_id = os.getenv("ARC_CHAIN_ID")
        return cls(
            notary_env=os.getenv("NOTARY_ENV", "development"),
            notary_demo_mode=_bool_env("NOTARY_DEMO_MODE", True),
            notary_default_privacy_mode=PrivacyMode(
                os.getenv("NOTARY_DEFAULT_PRIVACY_MODE", PrivacyMode.PROTECTED.value)
            ),
            validator_private_key=_optional_str("VALIDATOR_PRIVATE_KEY"),
            validator_eip712_name=os.getenv("VALIDATOR_EIP712_NAME", "NOTARY"),
            validator_eip712_version=os.getenv("VALIDATOR_EIP712_VERSION", "1"),
            arc_demo_mode=_bool_env("ARC_DEMO_MODE", True),
            arc_rpc_url=_optional_str("ARC_RPC_URL"),
            arc_chain_id=int(chain_id) if chain_id else None,
            arc_cli_path=os.getenv("ARC_CLI_PATH", "arc"),
            arc_operator_private_key=_optional_str("ARC_OPERATOR_PRIVATE_KEY"),
            arc_notary_identity_registry=_optional_str("ARC_NOTARY_IDENTITY_REGISTRY"),
            arc_attestation_registry=_optional_str("ARC_ATTESTATION_REGISTRY"),
            arc_karma_registry=_optional_str("ARC_KARMA_REGISTRY"),
            arc_validation_registry=_optional_str("ARC_VALIDATION_REGISTRY"),
            arc_governance=_optional_str("ARC_GOVERNANCE"),
            qevorpay_demo_mode=_bool_env("QEVORPAY_DEMO_MODE", True),
            qevorpay_api_base_url=_optional_str("QEVORPAY_API_BASE_URL"),
            qevorpay_api_key=_optional_str("QEVORPAY_API_KEY"),
            qevorpay_webhook_secret=_optional_str("QEVORPAY_WEBHOOK_SECRET"),
            speedmatic_demo_mode=_bool_env("SPEEDMATIC_DEMO_MODE", True),
            speedmatic_api_base_url=_optional_str("SPEEDMATIC_API_BASE_URL"),
            speedmatic_api_key=_optional_str("SPEEDMATIC_API_KEY"),
            evidence_vault_local_dir=Path(os.getenv("EVIDENCE_VAULT_LOCAL_DIR", ".notary_vault")),
            evidence_vault_passphrase=_optional_str("EVIDENCE_VAULT_PASSPHRASE"),
            notary_db_path=Path(os.getenv("NOTARY_DB_PATH", ".notary/notary.sqlite3")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
