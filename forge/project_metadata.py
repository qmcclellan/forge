import json
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path


def get_forge_version() -> str:
    try:
        return importlib_metadata.version("forge")
    except importlib_metadata.PackageNotFoundError:
        return "0.0.0-dev"


RECEIPT_VERSION = 2


def write_project_metadata(
    *,
    project_dir: Path,
    project_name: str,
    project_slug: str,
    template_name: str,
    docker_enabled: bool,
    jenkins_enabled: bool,
    git_initialized: bool,
    remote_configured: bool,
) -> Path:
    """Write the Forge metadata receipt.

    Receipt identity semantics are versioned:

    * Unversioned (historical) receipts have no `receipt_version` key and store
      the derived SLUG in `project_name`, because the display name and the slug
      were not separable at the time they were written. Those receipts remain
      valid historical artifacts and are not migrated.
    * Version 2 receipts define `project_name` as the human-readable display
      name and `project_slug` as the machine identity used for the generated
      directory and package name. When no explicit slug is supplied the two
      differ only in formatting, so version-2 receipts for slug-shaped names
      look the same as their historical counterparts.

    Consumers should branch on `receipt_version` rather than guessing.
    """
    metadata_dir = project_dir / ".forge"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = metadata_dir / "project.json"
    payload = {
        "receipt_version": RECEIPT_VERSION,
        "project_name": project_name,
        "project_slug": project_slug,
        "template_name": template_name,
        "created_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "forge_version": get_forge_version(),
        "docker_enabled": docker_enabled,
        "jenkins_enabled": jenkins_enabled,
        "git_initialized": git_initialized,
        "remote_configured": remote_configured,
    }

    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return metadata_path
