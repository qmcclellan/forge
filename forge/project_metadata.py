import json
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path


def get_forge_version() -> str:
    try:
        return importlib_metadata.version("forge")
    except importlib_metadata.PackageNotFoundError:
        return "0.0.0-dev"


def write_project_metadata(
    *,
    project_dir: Path,
    project_name: str,
    template_name: str,
    docker_enabled: bool,
    jenkins_enabled: bool,
    git_initialized: bool,
    remote_configured: bool,
) -> Path:
    metadata_dir = project_dir / ".forge"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = metadata_dir / "project.json"
    payload = {
        "project_name": project_name,
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
