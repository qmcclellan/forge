import subprocess
from pathlib import Path


def run_git_init(project_dir: Path) -> None:
    commands = [
        ["git", "init"],
        ["git", "branch", "-m", "main"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Initial scaffold from Forge"],
    ]

    for command in commands:
        subprocess.run(
            command,
            cwd=project_dir,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
