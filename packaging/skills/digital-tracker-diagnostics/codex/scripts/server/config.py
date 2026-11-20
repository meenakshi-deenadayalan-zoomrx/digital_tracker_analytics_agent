"""Optional diagnostics process configuration; no DB or dotenv dependency."""
import os
from pathlib import Path

class Settings:
    DTSA_GITHUB_TOKEN = os.environ.get('DTSA_GITHUB_TOKEN', '')
    DTSA_GITHUB_ORG = os.environ.get('DTSA_GITHUB_ORG', 'ZoomRx')
    DTSA_LOCAL_REPOS_BASE = os.environ.get('DTSA_LOCAL_REPOS_BASE', '')
    DTSA_PHABRICATOR_API_TOKEN = os.environ.get('DTSA_PHABRICATOR_API_TOKEN', '')
    DTSA_PHABRICATOR_API_URL = os.environ.get('DTSA_PHABRICATOR_API_URL', '')

env = Settings()
