"""
Verify the local project setup.

This script does not contact Google Cloud and does not call Gemini.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent import root_agent
from app.config import load_config
from app.knowledge import LocalKnowledgeProvider
from app.tools import AssistantTools

EXPECTED_TOOL_COUNT = 5


def print_check(message: str) -> None:
    """Print a successful verification step."""
    print(f"[ok] {message}")


def main() -> None:
    """Run all local verification checks."""

    print("\n=== Local Setup Verification ===\n")

    config = load_config()

    assert config.knowledge_source == "local"
    assert config.model
    assert config.local_knowledge_directory

    print_check("Configuration loaded")
    print(f"     Model: {config.model}")
    print(f"     Knowledge source: {config.knowledge_source}")

    knowledge_directory = Path(config.local_knowledge_directory)

    if not knowledge_directory.is_absolute():
        knowledge_directory = PROJECT_ROOT / knowledge_directory

    assert knowledge_directory.exists(), (
        f"Knowledge directory does not exist: {knowledge_directory}"
    )
    assert knowledge_directory.is_dir(), (
        f"Knowledge path is not a directory: {knowledge_directory}"
    )

    print_check("Knowledge directory found")
    print(f"     Path: {knowledge_directory}")

    provider = LocalKnowledgeProvider(knowledge_directory)
    tools = AssistantTools(provider)

    # -- documentation tools ------------------------------------------

    documents_result = tools.list_documents()
    assert documents_result["status"] == "success"
    assert documents_result["document_count"] > 0, (
        "No Markdown rule documents were found."
    )
    print_check("list_documents works")
    print(f"     Documents: {', '.join(documents_result['documents'])}")

    first_document = documents_result["documents"][0]
    read_result = tools.read_document(first_document)
    assert read_result["status"] == "success"
    assert read_result["content"].strip()
    print_check("read_document works")

    search_result = tools.search_documents("RESPONSE_FIELD_REMOVED")
    assert search_result["status"] == "success"
    assert search_result["matches"], (
        "Rule identifiers should be findable in the documentation."
    )
    print_check("search_documents finds rule identifiers")
    print(f"     Matched: "
          f"{', '.join(m['filename'] for m in search_result['matches'])}")

    # -- specification tools ------------------------------------------

    versions_result = tools.list_api_versions()
    assert versions_result["status"] == "success"
    assert versions_result["version_count"] >= 2, (
        "At least two OpenAPI specifications are required to compare."
    )
    print_check("list_api_versions works")
    print(f"     Versions: {', '.join(versions_result['versions'])}")

    old_version, new_version = versions_result["versions"][:2]
    comparison = tools.compare_api_versions(old_version, new_version)
    assert comparison["status"] == "success"
    assert "summary" in comparison and "findings" in comparison
    print_check("compare_api_versions works")
    print(f"     {old_version} -> {new_version}")
    print(f"     BREAKING: {comparison['summary']['breaking']}"
          f" | WARNING: {comparison['summary']['warning']}"
          f" | SAFE: {comparison['summary']['safe']}")

    identical = tools.compare_api_versions(old_version, old_version)
    assert identical["summary"]["compatible"] is True
    assert identical["findings"] == []
    print_check("Comparing a specification with itself reports no change")

    # -- error handling ------------------------------------------------

    missing_result = tools.read_document("missing-document.md")
    assert missing_result["status"] == "error"
    print_check("Missing-document handling works")

    empty_search_result = tools.search_documents("")
    assert empty_search_result["status"] == "error"
    print_check("Empty-search handling works")

    missing_spec = tools.compare_api_versions("missing.json", new_version)
    assert missing_spec["status"] == "error"
    print_check("Missing-specification handling works")

    # -- agent ---------------------------------------------------------

    assert root_agent.name == "api_breaking_change_assistant"
    assert len(root_agent.tools) == EXPECTED_TOOL_COUNT
    print_check("ADK agent loaded")
    print(f"     Agent: {root_agent.name}")
    print(f"     Tools: {len(root_agent.tools)}")

    print("\nAll local checks passed.")
    print("No Google Cloud request or Gemini request was made.\n")


if __name__ == "__main__":
    main()