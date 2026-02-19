"""Centralised configuration loaded from environment variables.

All secrets are read once at import time so every other module can
``from core.config import settings`` without touching os.environ directly.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StrappedSettings(BaseSettings):
    """Application-wide settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # PostgreSQL
    database_url: str = Field(
        default="postgresql://localhost:5432/strapped",
        description="PostgreSQL connection string",
    )

    # Azure OpenAI
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key")
    azure_openai_deployment_name: str = Field(default="", description="Model deployment name")
    azure_openai_endpoint: str = Field(default="", description="Azure OpenAI resource endpoint")

    # Microsoft Graph / Entra ID
    azure_tenant_id: str = Field(default="", description="Entra ID tenant")
    azure_client_id: str = Field(default="", description="App registration client ID")
    azure_client_secret: str = Field(default="", description="App registration secret")

    # Strapped operational
    strapped_mailbox: str = Field(
        default="strapped@yourcompany.com",
        alias="vela_mailbox",
        description="Shared mailbox Strapped AI monitors",
    )
    strapped_log_level: str = Field(default="INFO", alias="vela_log_level")
    strapped_auto_approve_threshold: int = Field(
        default=85, ge=0, le=100,
        alias="vela_auto_approve_threshold",
        description="Confidence % above which Strapped sends replies without escalation",
    )
    strapped_default_timezone: str = Field(
        default="America/New_York",
        alias="vela_default_timezone",
    )


settings = StrappedSettings()  # type: ignore[call-arg]
