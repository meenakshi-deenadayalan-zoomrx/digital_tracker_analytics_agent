"""DTSA MCP Server — configuration (DTSA fields only)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Extension DB read replica
    DTSA_EXTENSION_DB_READ_HOST: str = ""
    DTSA_EXTENSION_DB_READ_PORT: int = 3306
    DTSA_EXTENSION_DB_READ_NAME: str = "extn"
    DTSA_EXTENSION_DB_READ_USERNAME: str = ""
    DTSA_EXTENSION_DB_READ_PASSWORD: str = ""

    # GitHub (PAT with repo:read scope — leave empty to use local repos)
    DTSA_GITHUB_TOKEN: str = ""
    DTSA_GITHUB_ORG: str = "ZoomRx"

    # Local repo paths (used when DTSA_GITHUB_TOKEN is not set)
    DTSA_LOCAL_REPOS_BASE: str = ""

    # Phabricator (Conduit API — create-only token)
    DTSA_PHABRICATOR_API_TOKEN: str = ""
    DTSA_PHABRICATOR_API_URL: str = ""


env = Settings()
