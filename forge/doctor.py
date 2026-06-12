import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def _status(ok: bool, *, required: bool = True) -> str:
    if ok:
        return "ok"
    return "fail" if required else "warn"


def run_doctor() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parent.parent
    templates_dir = repo_root / "templates"
    cwd = Path.cwd()

    python_ok = sys.version_info >= (3, 10)
    git_ok = shutil.which("git") is not None
    docker_ok = shutil.which("docker") is not None
    cwd_writable = os.access(cwd, os.W_OK)
    templates_ok = templates_dir.exists() and templates_dir.is_dir()

    checks = {
        "python": {
            "status": _status(python_ok),
            "required": True,
            "detail": sys.version.split()[0],
        },
        "git": {
            "status": _status(git_ok),
            "required": True,
            "detail": shutil.which("git") or "not found",
        },
        "docker": {
            "status": _status(docker_ok, required=False),
            "required": False,
            "detail": shutil.which("docker") or "not found",
        },
        "cwd_writable": {
            "status": _status(cwd_writable),
            "required": True,
            "detail": str(cwd),
        },
        "templates": {
            "status": _status(templates_ok),
            "required": True,
            "detail": str(templates_dir),
        },
        "nexus": {
            "status": "skip",
            "required": False,
            "detail": "not configured",
        },
    }

    overall_ok = all(
        item["status"] == "ok"
        for item in checks.values()
        if item["required"]
    )

    return {
        "ok": overall_ok,
        "checks": checks,
    }


def doctor_json() -> str:
    return json.dumps(run_doctor(), indent=2, sort_keys=True)


def doctor_text() -> str:
    result = run_doctor()
    lines = ["Forge Doctor", ""]

    for name, item in result["checks"].items():
        lines.append(f"[{item['status']}] {name}: {item['detail']}")

    lines.append("")
    lines.append(f"overall: {'ok' if result['ok'] else 'fail'}")
    return "\n".join(lines)
