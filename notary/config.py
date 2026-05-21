from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from notary.models.schemas import PrivacyMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    notary_env: str = Field(default="development", alias="NOTARY_ENV")
    notary_demo_mode: bool = Field(default=True, alias="NOTARY_DEMO_MODE")
    notary_default_privacy_mode: PrivacyMode = Field(
        default=PrivacyMode.PROTECTED, alias="NOTARY_DEFAULT_PRIVACY_MODE"
    )

    arc_demo_mode: bool = Field(default=True, alias="ARC_DEMO_MODE")
    arc_rpc_url: str | None = Field(default=None, alias="ARC_RPC_URL")
    arc_chain_id: int | None = Field(default=None, alias="ARC_CHAIN_ID")
    arc_cli_path: str = Field(default="arc", alias="ARC_CLI_PATH")

    qevorpay_demo_mode: bool = Field(default=True, alias="QEVORPAY_DEMO_MODE")
    qevorpay_api_base_url: str | None = Field(default=None, alias="QEVORPAY_API_BASE_URL")
    qevorpay_api_key: str | None = Field(default=None, alias="QEVORPAY_API_KEY")
    qevorpay_webhook_secret: str | None = Field(default=None, alias="QEVORPAY_WEBHOOK_SECRET")

    speedmatic_demo_mode: bool = Field(default=True, alias="SPEEDMATIC_DEMO_MODE")
    speedmatic_api_base_url: str | None = Field(default=None, alias="SPEEDMATIC_API_BASE_URL")
    speedmatic_api_key: str | None = Field(default=None, alias="SPEEDMATIC_API_KEY")

    evidence_vault_local_dir: Path = Field(
        default=Path(".notary_vault"), alias="EVIDENCE_VAULT_LOCAL_DIR"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

