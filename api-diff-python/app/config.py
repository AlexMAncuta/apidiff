"""
Application configuration.

The project initially uses a local knowledge base. Google Cloud settings
become mandatory only when the cloud knowledge source is selected.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

KnowledgeSource = Literal["local", "cloud"]


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    model: str
    knowledge_source: KnowledgeSource
    local_knowledge_directory: str

    project_id: str | None
    location: str
    knowledge_bucket: str | None


def load_config() -> Config:
    """
    Load and validate configuration from environment variables.

    Cloud-specific variables are required only when
    KNOWLEDGE_SOURCE=cloud.

    Raises:
        ValueError: If the configuration is invalid.
    """

    model = os.getenv("MODEL", "gemini-2.5-flash")

    knowledge_source = os.getenv(
        "KNOWLEDGE_SOURCE",
        "local",
    ).strip().lower()

    if knowledge_source not in {"local", "cloud"}:
        raise ValueError(
            "KNOWLEDGE_SOURCE must be either 'local' or 'cloud'."
        )

    local_knowledge_directory = os.getenv(
        "LOCAL_KNOWLEDGE_DIRECTORY",
        "knowledge",
    )

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or None
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    knowledge_bucket = os.getenv("KNOWLEDGE_BUCKET") or None

    if knowledge_source == "cloud":
        missing: list[str] = []

        if not project_id:
            missing.append("GOOGLE_CLOUD_PROJECT")

        if not knowledge_bucket:
            missing.append("KNOWLEDGE_BUCKET")

        if missing:
            raise ValueError(
                "Cloud knowledge mode requires: "
                + ", ".join(missing)
            )

    return Config(
        model=model,
        knowledge_source=knowledge_source,
        local_knowledge_directory=local_knowledge_directory,
        project_id=project_id,
        location=location,
        knowledge_bucket=knowledge_bucket,
    )