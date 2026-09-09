"""
Upload the local knowledge base to Cloud Storage.

Uploads both the Markdown rule documents and the OpenAPI specifications.
Use --dry-run to inspect the upload plan without contacting Google Cloud.
"""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.cloud import storage

from app.config import load_config
from app.knowledge import KNOWLEDGE_EXTENSIONS

KNOWLEDGE_DIRECTORY = PROJECT_ROOT / "knowledge"

CONTENT_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Upload knowledge documents to Google Cloud Storage."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which files would be uploaded without contacting GCP.",
    )

    parser.add_argument(
        "--bucket",
        help="Target bucket name. If omitted, KNOWLEDGE_BUCKET is read "
             "from .env.",
    )

    return parser.parse_args()


def discover_documents() -> list[Path]:
    """Return the local documents to upload."""

    return sorted(
        path
        for path in KNOWLEDGE_DIRECTORY.iterdir()
        if path.is_file() and path.suffix in KNOWLEDGE_EXTENSIONS
    )


def show_upload_plan(documents: list[Path], bucket_name: str | None) -> None:
    """Print the planned upload operations."""

    print("\n=== Knowledge Upload Plan ===\n")
    print("Target bucket:", bucket_name or "<not configured>")
    print("Local directory:", KNOWLEDGE_DIRECTORY)
    print(f"Documents: {len(documents)}\n")

    for document in documents:
        target = (
            f"gs://{bucket_name}/{document.name}"
            if bucket_name
            else f"<bucket>/{document.name}"
        )
        print(f"- {document.name}")
        print(f"  -> {target}")


def upload_documents(
        documents: list[Path],
        bucket_name: str,
        project_id: str | None,
) -> None:
    """Upload the discovered files to Cloud Storage."""

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    print("\n=== Uploading Knowledge Documents ===\n")

    for document in documents:
        blob = bucket.blob(document.name)

        blob.upload_from_filename(
            str(document),
            content_type=CONTENT_TYPES.get(
                document.suffix,
                "application/octet-stream",
            ),
        )

        print(f"Uploaded {document.name} "
              f"to gs://{bucket_name}/{document.name}")

    print(f"\nUploaded {len(documents)} documents.\n")


def main() -> None:
    """Run the knowledge upload utility."""

    arguments = parse_arguments()
    config = load_config()

    documents = discover_documents()

    if not documents:
        raise SystemExit(
            "No knowledge files were found in the knowledge directory."
        )

    bucket_name = arguments.bucket or config.knowledge_bucket

    show_upload_plan(documents=documents, bucket_name=bucket_name)

    if arguments.dry_run:
        print("\nDry run completed. No Google Cloud request was made.\n")
        return

    if not bucket_name:
        raise SystemExit(
            "No bucket was configured. Set KNOWLEDGE_BUCKET in .env "
            "or use --bucket BUCKET_NAME."
        )

    upload_documents(
        documents=documents,
        bucket_name=bucket_name,
        project_id=config.project_id,
    )


if __name__ == "__main__":
    main()