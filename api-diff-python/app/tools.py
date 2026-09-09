"""
Tools available to the API Breaking-Change Assistant.

Two families of tools:

  Documentation tools  (list_documents, read_document, search_documents)
      operate on the *.md files describing compatibility rules.

  Specification tools  (list_api_versions, compare_api_versions)
      operate on the *.json OpenAPI documents.

Both families read through the same KnowledgeProvider, so switching from
local files to Cloud Storage changes nothing here.
"""

import json

from app.comparator import compare_specs
from app.knowledge import KnowledgeProvider

DOC_SUFFIX = ".md"
SPEC_SUFFIX = ".json"


class AssistantTools:
    """Operations that the AI agent can perform."""

    def __init__(self, knowledge_provider: KnowledgeProvider):
        self.knowledge = knowledge_provider

    # ------------------------------------------------------------------
    # Documentation tools
    # ------------------------------------------------------------------

    def list_documents(self) -> dict:
        """
        List the available documentation about API compatibility rules.

        Use this tool when the user asks what guidance, policies, or
        reference material is available.

        Returns:
            A dictionary containing the operation status and filenames.
        """
        documents = [
            name
            for name in self.knowledge.list_documents()
            if name.endswith(DOC_SUFFIX)
        ]

        return {
            "status": "success",
            "documents": documents,
            "document_count": len(documents),
        }

    def read_document(self, filename: str) -> dict:
        """
        Read one documentation file about API compatibility rules.

        Use this tool after search_documents identifies a relevant file,
        or when the user names a document explicitly.

        Args:
            filename: Exact Markdown filename, such as "breaking-changes.md".

        Returns:
            A dictionary containing the document content or an error.
        """
        try:
            content = self.knowledge.read_document(filename)
        except FileNotFoundError:
            return {
                "status": "error",
                "filename": filename,
                "error_message": f"Document '{filename}' was not found.",
            }

        return {
            "status": "success",
            "filename": filename,
            "content": content,
        }

    def search_documents(self, keyword: str) -> dict:
        """
        Search the compatibility documentation and return matching excerpts.

        Use this tool to find the rule that justifies a verdict. Rule
        identifiers such as "RESPONSE_FIELD_REMOVED" are good keywords,
        and so are concepts such as "deprecation" or "enum".

        Args:
            keyword: Word or phrase to search for, such as "PARAM_NOW_REQUIRED".

        Returns:
            A dictionary containing matching filenames and line excerpts.
        """
        normalized_keyword = keyword.strip().casefold()

        if not normalized_keyword:
            return {
                "status": "error",
                "keyword": keyword,
                "error_message": "The search keyword cannot be empty.",
            }

        matches: list[dict] = []

        for filename in self.knowledge.list_documents():
            if not filename.endswith(DOC_SUFFIX):
                continue

            content = self.knowledge.read_document(filename)
            excerpts: list[dict] = []

            for line_number, line in enumerate(content.splitlines(), start=1):
                if normalized_keyword in line.casefold():
                    excerpts.append(
                        {
                            "line_number": line_number,
                            "text": line.strip(),
                        }
                    )
                if len(excerpts) == 3:
                    break

            if excerpts:
                matches.append({"filename": filename, "excerpts": excerpts})

        return {
            "status": "success",
            "keyword": keyword,
            "matches": matches,
            "match_count": len(matches),
        }

    # ------------------------------------------------------------------
    # Specification tools
    # ------------------------------------------------------------------

    def list_api_versions(self) -> dict:
        """
        List the OpenAPI specification versions available for comparison.

        Use this tool before comparing versions, or when the user asks
        which API versions exist.

        Returns:
            A dictionary containing the available specification filenames.
        """
        versions = [
            name
            for name in self.knowledge.list_documents()
            if name.endswith(SPEC_SUFFIX)
        ]

        return {
            "status": "success",
            "versions": versions,
            "version_count": len(versions),
        }

    def compare_api_versions(
            self,
            old_version: str,
            new_version: str,
    ) -> dict:
        """
        Compare two OpenAPI specifications and detect breaking changes.

        This tool decides the verdict. Never judge compatibility yourself;
        report and explain what this tool returns.

        Args:
            old_version: Filename of the older specification,
                such as "openapi-v1.json".
            new_version: Filename of the newer specification,
                such as "openapi-v2.json".

        Returns:
            A dictionary with a summary (counts and a compatible flag) and
            a list of findings. Each finding has a severity of BREAKING,
            WARNING, or SAFE, a rule identifier, a location, and a detail.
        """
        specs = {}

        for label, filename in (
                ("old_version", old_version),
                ("new_version", new_version),
        ):
            try:
                raw = self.knowledge.read_document(filename)
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error_message": (
                        f"Specification '{filename}' was not found. "
                        f"Call list_api_versions to see available files."
                    ),
                }

            try:
                specs[label] = json.loads(raw)
            except json.JSONDecodeError as error:
                return {
                    "status": "error",
                    "error_message": (
                        f"'{filename}' is not valid JSON: {error}"
                    ),
                }

        result = compare_specs(specs["old_version"], specs["new_version"])

        return {
            "status": "success",
            "old_version": old_version,
            "new_version": new_version,
            "summary": result["summary"],
            "findings": result["findings"],
        }