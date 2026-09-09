"""
Local demonstration of the assistant's tools.

Runs the same operations the agent will perform, without contacting
Google Cloud and without calling Gemini.
"""

from pathlib import Path

from app.knowledge import LocalKnowledgeProvider
from app.tools import AssistantTools

SEVERITY_ORDER = ("BREAKING", "WARNING", "SAFE")


def main() -> None:
    """Demonstrate the local tools without using Google Cloud."""

    print("\n=== API Breaking-Change Assistant ===\n")

    provider = LocalKnowledgeProvider(Path("knowledge"))
    tools = AssistantTools(provider)

    # -- rule documentation -------------------------------------------

    print("Rule documents")
    print("--------------")

    documents_result = tools.list_documents()

    for document in documents_result["documents"]:
        print(f"- {document}")

    # -- available specifications -------------------------------------

    print("\nAPI versions")
    print("------------")

    versions_result = tools.list_api_versions()

    for version in versions_result["versions"]:
        print(f"- {version}")

    if versions_result["version_count"] < 2:
        print("\nAt least two specifications are needed to compare.")
        return

    old_version, new_version = versions_result["versions"][:2]

    # -- comparison ----------------------------------------------------

    print(f"\nComparing {old_version} -> {new_version}")
    print("-" * 60)

    comparison = tools.compare_api_versions(old_version, new_version)

    if comparison["status"] == "error":
        print(comparison["error_message"])
        return

    summary = comparison["summary"]

    print(f"BREAKING: {summary['breaking']}"
          f" | WARNING: {summary['warning']}"
          f" | SAFE: {summary['safe']}")
    print(f"Safe to upgrade: {'yes' if summary['compatible'] else 'no'}\n")

    for severity in SEVERITY_ORDER:
        findings = [
            f for f in comparison["findings"] if f["severity"] == severity
        ]

        if not findings:
            continue

        print(f"{severity} ({len(findings)})")

        for finding in findings:
            print(f"  {finding['rule']:<32} {finding['location']}")
            print(f"  {'':32} {finding['detail']}")

        print()

    # -- justification -------------------------------------------------

    first_breaking = next(
        (f for f in comparison["findings"] if f["severity"] == "BREAKING"),
        None,
    )

    if first_breaking is None:
        return

    print(f"Documentation for {first_breaking['rule']}")
    print("-" * 60)

    search_result = tools.search_documents(first_breaking["rule"])

    for match in search_result["matches"]:
        print(f"\n{match['filename']}")
        for excerpt in match["excerpts"]:
            print(f"  line {excerpt['line_number']}: {excerpt['text']}")

    print()


if __name__ == "__main__":
    main()