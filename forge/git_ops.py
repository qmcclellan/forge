import subprocess
from pathlib import Path


def run_git_command(project_dir: Path, command: list[str]) -> None:
    subprocess.run(
        command,
        cwd=project_dir,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_git_init(project_dir: Path) -> None:
    commands = [
        ["git", "init"],
        ["git", "branch", "-m", "main"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Initial scaffold from Forge"],
    ]

    for command in commands:
        run_git_command(project_dir, command)


def add_remote_origin(project_dir: Path, remote_url: str) -> None:
    run_git_command(project_dir, ["git", "remote", "add", "origin", remote_url])
