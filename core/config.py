"""Centralised configuration loaded from environment variables.

All Azure secrets are read once at import time so every other module can
``from core.config import settings`` without touching os.environ directly.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VelaSettings(BaseSettings):
    """Application-wide settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_deployment_name: str = Field(..., description="Model deployment name")
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI resource endpoint")

    # Azure Table Storage
    azure_storage_connection_string: str = Field(
        ..., description="Connection string for Azure Table Storage"
    )

    # Microsoft Graph / Entra ID
    azure_tenant_id: str = Field(default="", description="Entra ID tenant")
    azure_client_id: str = Field(default="", description="App registration client ID")
    azure_client_secret: str = Field(default="", description="App registration secret")

    # Vela operational
    vela_mailbox: str = Field(
        default="vela@ourfirm.onmicrosoft.com",
        description="Shared mailbox Vela monitors",
    )
    vela_log_level: str = Field(default="INFO")
    vela_auto_approve_threshold: int = Field(
        default=85,
        ge=0,
        le=100,
        description="Confidence % above which Vela sends replies without escalation",
    )
    vela_default_timezone: str = Field(default="America/New_York")


settings = VelaSettings()  # type: ignore[call-arg]
