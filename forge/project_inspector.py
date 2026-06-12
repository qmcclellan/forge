import json
import subprocess
from pathlib import Path
from typing import Any


def _git_check(path: Path, args: list[str]) -> bool:
    try:
        subprocess.run(
            ["git", *args],
            cwd=path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def inspect_project(path: str | Path) -> dict[str, Any]:
    project_path = Path(path).expanduser().resolve()

    checks = {
        "readme": (project_path / "README.md").exists(),
        "runbook": (project_path / "docs" / "runbook.md").exists(),
        "interview_talk_track": (project_path / "docs" / "interview-talk-track.md").exists(),
        "tests": (project_path / "tests").exists(),
        "pyproject": (project_path / "pyproject.toml").exists(),
        "dockerfile": (project_path / "Dockerfile").exists(),
        "docker_compose": (project_path / "docker-compose.yml").exists(),
        "jenkinsfile": (project_path / "Jenkinsfile").exists(),
        "git_repo": (project_path / ".git").exists(),
        "git_remote": _git_check(project_path, ["remote", "get-url", "origin"]),
        "forge_metadata": (project_path / ".forge" / "project.json").exists(),
    }

    return {
        "path": str(project_path),
        "checks": checks,
    }


def inspect_project_json(path: str | Path) -> str:
    return json.dumps(inspect_project(path), indent=2, sort_keys=True)
