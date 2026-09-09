"""
Generate reproducible dependency files from the active virtual environment.

Outputs:
    requirements-pinned.txt
        Direct workshop dependencies with exact versions.

    requirements-lock.txt
        Every installed package and exact version from pip freeze.
"""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIRECT_DEPENDENCIES = [
    "google-adk",
    "google-genai",
    "google-cloud-storage",
    "google-cloud-aiplatform",
    "python-dotenv",
    "rich",
]


def generate_pinned_requirements() -> list[str]:
    """Return exact versions for the direct project dependencies."""

    requirements: list[str] = []
    missing: list[str] = []

    for package_name in DIRECT_DEPENDENCIES:
        try:
            installed_version = version(package_name)
        except PackageNotFoundError:
            missing.append(package_name)
            continue

        requirements.append(
            f"{package_name}=={installed_version}"
        )

    if missing:
        raise RuntimeError(
            "The following direct dependencies are not installed: "
            + ", ".join(missing)
        )

    return requirements


def generate_full_lock() -> str:
    """Return the complete pip freeze output."""

    completed_process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "freeze",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return completed_process.stdout


def main() -> None:
    """Generate both dependency files."""

    pinned_requirements = generate_pinned_requirements()

    pinned_path = PROJECT_ROOT / "requirements-pinned.txt"
    lock_path = PROJECT_ROOT / "requirements-lock.txt"

    pinned_path.write_text(
        "\n".join(pinned_requirements) + "\n",
        encoding="utf-8",
    )

    lock_path.write_text(
        generate_full_lock(),
        encoding="utf-8",
    )

    print("\nDependency files generated successfully.\n")

    print(f"Direct dependencies: {pinned_path}")
    for requirement in pinned_requirements:
        print(f"  {requirement}")

    print(f"\nComplete environment lock: {lock_path}\n")


if __name__ == "__main__":
    main()