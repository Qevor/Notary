from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel

from notary.models.schemas import PrivacyMode


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


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
    notary_demo_mode: bool = False
    notary_default_privacy_mode: PrivacyMode = PrivacyMode.PROTECTED
    notary_session_secret: str | None = None

    claude_api_key: str | None = None
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_api_base_url: str = "https://api.anthropic.com"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_base_url: str = "https://api.groq.com"

    validator_private_key: str | None = None
    validator_eip712_name: str = "NOTARY"
    validator_eip712_version: str = "1"

    arc_demo_mode: bool = False
    arc_rpc_url: str | None = None
    arc_chain_id: int | None = None
    arc_cli_path: str = "arc"
    arc_operator_private_key: str | None = None
    arc_notary_identity_registry: str | None = None
    arc_attestation_registry: str | None = None
    arc_validation_registry: str | None = None
    arc_governance: str | None = None

    circle_cli_path: str = "circle"
    circle_wallet_email: str | None = None
    circle_chain: str = "ARC-TESTNET"
    circle_testnet: bool = True
    circle_gateway_enabled: bool = True
    circle_paymaster_enabled: bool = True

    qevorpay_demo_mode: bool = False
    qevorpay_api_base_url: str | None = None
    qevorpay_api_key: str | None = None
    qevorpay_webhook_secret: str | None = None
    qevorpay_payment_link_path: str | None = None
    qevorpay_batch_distribution_path: str | None = None
    qevorpay_release_escrow_path: str | None = None
    qevorpay_refund_path: str | None = None
    qevorpay_payment_status_path_template: str | None = None
    qevorpay_webhook_signature_header: str = "x-signature"
    qevor_supabase_url: str | None = None
    qevor_supabase_anon_key: str | None = None
    qevor_supabase_service_role_key: str | None = None
    qevor_executor_agent_wallet_id: str | None = None
    qevor_creator_wallet: str | None = None

    speechmatics_demo_mode: bool = False
    speechmatics_api_base_url: str | None = "https://asr.api.speechmatics.com/v2"
    speechmatics_api_key: str | None = None
    speechmatics_transcriptions_path: str | None = "/jobs"
    speechmatics_transcription_status_path_template: str | None = "/jobs/{job_id}"
    speechmatics_transcript_path_template: str | None = "/jobs/{job_id}/transcript?format=json-v2"
    speechmatics_language: str = "en"
    speechmatics_operating_point: str = "enhanced"
    speechmatics_diarization: str = "speaker"

    evidence_vault_local_dir: Path = Path(".notary_vault")
    evidence_vault_passphrase: str | None = None
    notary_db_path: Path = Path(".notary/notary.sqlite3")

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        chain_id = os.getenv("ARC_CHAIN_ID")
        return cls(
            notary_env=os.getenv("NOTARY_ENV", "development"),
            notary_demo_mode=_bool_env("NOTARY_DEMO_MODE", False),
            notary_default_privacy_mode=PrivacyMode(
                os.getenv("NOTARY_DEFAULT_PRIVACY_MODE", PrivacyMode.PROTECTED.value)
            ),
            notary_session_secret=_optional_str("NOTARY_SESSION_SECRET"),
            claude_api_key=_optional_str("CLAUDE_API_KEY"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            claude_api_base_url=os.getenv("CLAUDE_API_BASE_URL", "https://api.anthropic.com"),
            groq_api_key=_optional_str("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            groq_api_base_url=os.getenv("GROQ_API_BASE_URL", "https://api.groq.com"),
            validator_private_key=_optional_str("VALIDATOR_PRIVATE_KEY"),
            validator_eip712_name=os.getenv("VALIDATOR_EIP712_NAME", "NOTARY"),
            validator_eip712_version=os.getenv("VALIDATOR_EIP712_VERSION", "1"),
            arc_demo_mode=_bool_env("ARC_DEMO_MODE", False),
            arc_rpc_url=_optional_str("ARC_RPC_URL"),
            arc_chain_id=int(chain_id) if chain_id else None,
            arc_cli_path=os.getenv("ARC_CLI_PATH", "arc"),
            arc_operator_private_key=_optional_str("ARC_OPERATOR_PRIVATE_KEY"),
            arc_notary_identity_registry=_optional_str("ARC_NOTARY_IDENTITY_REGISTRY"),
            arc_attestation_registry=_optional_str("ARC_ATTESTATION_REGISTRY"),
            arc_validation_registry=_optional_str("ARC_VALIDATION_REGISTRY"),
            arc_governance=_optional_str("ARC_GOVERNANCE"),
            circle_cli_path=os.getenv("CIRCLE_CLI_PATH", "circle"),
            circle_wallet_email=_optional_str("CIRCLE_WALLET_EMAIL"),
            circle_chain=os.getenv("CIRCLE_CHAIN", "ARC-TESTNET"),
            circle_testnet=_bool_env("CIRCLE_TESTNET", True),
            circle_gateway_enabled=_bool_env("CIRCLE_GATEWAY_ENABLED", True),
            circle_paymaster_enabled=_bool_env("CIRCLE_PAYMASTER_ENABLED", True),
            qevorpay_demo_mode=_bool_env("QEVORPAY_DEMO_MODE", False),
            qevorpay_api_base_url=_optional_str("QEVORPAY_API_BASE_URL"),
            qevorpay_api_key=_optional_str("QEVORPAY_API_KEY"),
            qevorpay_webhook_secret=_optional_str("QEVORPAY_WEBHOOK_SECRET"),
            qevorpay_payment_link_path=_optional_str("QEVORPAY_PAYMENT_LINK_PATH"),
            qevorpay_batch_distribution_path=_optional_str("QEVORPAY_BATCH_DISTRIBUTION_PATH"),
            qevorpay_release_escrow_path=_optional_str("QEVORPAY_RELEASE_ESCROW_PATH"),
            qevorpay_refund_path=_optional_str("QEVORPAY_REFUND_PATH"),
            qevorpay_payment_status_path_template=_optional_str("QEVORPAY_PAYMENT_STATUS_PATH_TEMPLATE"),
            qevorpay_webhook_signature_header=os.getenv("QEVORPAY_WEBHOOK_SIGNATURE_HEADER", "x-signature"),
            qevor_supabase_url=_optional_str("QEVOR_SUPABASE_URL") or _optional_str("SUPABASE_URL"),
            qevor_supabase_anon_key=(
                _optional_str("QEVOR_SUPABASE_ANON_KEY")
                or _optional_str("SUPABASE_ANON_KEY")
            ),
            qevor_supabase_service_role_key=(
                _optional_str("QEVOR_SUPABASE_SERVICE_ROLE_KEY")
                or _optional_str("SUPABASE_SERVICE_ROLE_KEY")
            ),
            qevor_executor_agent_wallet_id=_optional_str("QEVOR_EXECUTOR_AGENT_WALLET_ID"),
            qevor_creator_wallet=_optional_str("QEVOR_CREATOR_WALLET"),
            speechmatics_demo_mode=_bool_env(
                "SPEECHMATICS_DEMO_MODE",
                _bool_env("SPEEDMATIC_DEMO_MODE", False),
            ),
            speechmatics_api_base_url=(
                _optional_str("SPEECHMATICS_API_BASE_URL")
                or _optional_str("SPEEDMATIC_API_BASE_URL")
                or "https://asr.api.speechmatics.com/v2"
            ),
            speechmatics_api_key=_optional_str("SPEECHMATICS_API_KEY")
            or _optional_str("SPEEDMATIC_API_KEY"),
            speechmatics_transcriptions_path=(
                _optional_str("SPEECHMATICS_TRANSCRIPTIONS_PATH")
                or _optional_str("SPEEDMATIC_TRANSCRIPTIONS_PATH")
                or "/jobs"
            ),
            speechmatics_transcription_status_path_template=(
                _optional_str("SPEECHMATICS_TRANSCRIPTION_STATUS_PATH_TEMPLATE")
                or _optional_str("SPEEDMATIC_TRANSCRIPTION_STATUS_PATH_TEMPLATE")
                or "/jobs/{job_id}"
            ),
            speechmatics_transcript_path_template=(
                _optional_str("SPEECHMATICS_TRANSCRIPT_PATH_TEMPLATE")
                or "/jobs/{job_id}/transcript?format=json-v2"
            ),
            speechmatics_language=os.getenv("SPEECHMATICS_LANGUAGE", "en"),
            speechmatics_operating_point=os.getenv("SPEECHMATICS_OPERATING_POINT", "enhanced"),
            speechmatics_diarization=os.getenv("SPEECHMATICS_DIARIZATION", "speaker"),
            evidence_vault_local_dir=Path(os.getenv("EVIDENCE_VAULT_LOCAL_DIR", ".notary_vault")),
            evidence_vault_passphrase=_optional_str("EVIDENCE_VAULT_PASSPHRASE"),
            notary_db_path=Path(os.getenv("NOTARY_DB_PATH", ".notary/notary.sqlite3")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
