"""Server-side settings. The Sarvam key is read here and nowhere else.

Rule 8 of prompt.md: secrets stay server-side. No client ever sees SARVAM_API_KEY.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved absolutely so the key is found whether the process starts from the
# repo root, from backend/, or from pytest.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    SARVAM_API_KEY: str = ""

    # DECISION: with no key present the Sarvam wrappers serve recorded fixture
    # responses instead of failing, so the two slices are demonstrable without
    # an account. Every such response is tagged source="mock" all the way out to
    # the HTTP body, so a mock can never be mistaken for a real transcription.
    SARVAM_MOCK: bool = False

    # Confidence floor for anything a model hands back for a human to accept.
    CONFIDENCE_THRESHOLD: float = 0.85

    # Voice Agents platform (Indus). Separate from the model-API key above: this
    # is the workspace key sent as X-API-Key. Without all three of these the
    # clinic call cannot be placed on a real phone line, so the clinic agent runs
    # its dialogue locally and says so rather than pretending a call happened.
    SARVAM_VA_API_KEY: str = ""
    SARVAM_ORG_ID: str = ""
    SARVAM_WORKSPACE_ID: str = ""
    SARVAM_VA_BASE_URL: str = "https://apps.sarvam.ai"

    @property
    def live(self) -> bool:
        return bool(self.SARVAM_API_KEY) and not self.SARVAM_MOCK

    @property
    def indus_ready(self) -> bool:
        """True when a real outbound call can be placed."""
        return all(
            [self.SARVAM_VA_API_KEY, self.SARVAM_ORG_ID, self.SARVAM_WORKSPACE_ID]
        )

    def missing_indus_vars(self) -> list[str]:
        return [
            name
            for name in ("SARVAM_VA_API_KEY", "SARVAM_ORG_ID", "SARVAM_WORKSPACE_ID")
            if not getattr(self, name)
        ]


@lru_cache
def settings() -> Settings:
    return Settings()
