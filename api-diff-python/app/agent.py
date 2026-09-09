"""
ADK agent definition for the API Breaking-Change Assistant.
"""

from pathlib import Path

from google.adk.agents.llm_agent import Agent

from app.config import load_config
from app.knowledge import (
    CloudKnowledgeProvider,
    KnowledgeProvider,
    LocalKnowledgeProvider,
)
from app.prompts import SYSTEM_PROMPT
from app.tools import AssistantTools

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_knowledge_provider() -> KnowledgeProvider:
    """Create the provider selected in the application configuration."""

    config = load_config()

    if config.knowledge_source == "local":
        knowledge_directory = Path(config.local_knowledge_directory)

        if not knowledge_directory.is_absolute():
            knowledge_directory = PROJECT_ROOT / knowledge_directory

        return LocalKnowledgeProvider(knowledge_directory)

    if config.knowledge_source == "cloud":
        if not config.knowledge_bucket:
            raise ValueError("KNOWLEDGE_BUCKET is required in cloud mode.")

        return CloudKnowledgeProvider(
            bucket_name=config.knowledge_bucket,
            project_id=config.project_id,
        )

    raise ValueError(
        f"Unsupported knowledge source: {config.knowledge_source}"
    )


config = load_config()
knowledge_provider = create_knowledge_provider()
assistant_tools = AssistantTools(knowledge_provider)

root_agent = Agent(
    name="api_breaking_change_assistant",
    model=config.model,
    description=(
        "Compares two OpenAPI specifications, detects breaking changes, "
        "and explains their impact on existing API clients."
    ),
    instruction=SYSTEM_PROMPT,
    tools=[
        assistant_tools.list_api_versions,
        assistant_tools.compare_api_versions,
        assistant_tools.list_documents,
        assistant_tools.read_document,
        assistant_tools.search_documents,
    ],
)
