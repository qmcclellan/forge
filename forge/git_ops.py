import subprocess
from pathlib import Path


# Identity used ONLY when the environment supplies none, and ONLY for Forge's own
# scaffold commit. A machine that has never had `git config user.email` set --
# a fresh container, a CI runner, a new workstation -- otherwise makes
# `forge new --git-init` fail outright with git exit 128.
#
# `.invalid` is reserved by RFC 2606 and can never resolve, so this address can
# never be mistaken for a contactable person. The name is the tool, not a user.
FALLBACK_COMMITTER_NAME = "Forge"
FALLBACK_COMMITTER_EMAIL = "forge@forge.invalid"


def run_git_command(project_dir: Path, command: list[str]) -> None:
    subprocess.run(
        command,
        cwd=project_dir,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def has_usable_git_identity(project_dir: Path) -> bool:
    """True when git can already resolve BOTH identities a commit requires.

    `git var GIT_AUTHOR_IDENT` / `GIT_COMMITTER_IDENT` are git's own resolution
    of the identities it would use, so system, global, repository and
    environment sources are all honoured without Forge reimplementing that
    precedence. Each exits non-zero precisely when git would refuse to commit
    for want of that half.

    BOTH are checked because they resolve independently. An environment that
    sets only GIT_COMMITTER_NAME/EMAIL resolves a committer but no author, and a
    plain commit there still fails with exit 128 -- so checking the committer
    alone would report a usable identity that does not, in fact, permit a
    commit.
    """
    for variable in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        result = subprocess.run(
            ["git", "var", variable],
            cwd=project_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            return False

    return True


def scaffold_commit_command(project_dir: Path) -> list[str]:
    """The commit argv for the scaffold commit, with identity only if needed.

    An identity the caller already provides always wins: when git can resolve
    one, the command carries no overrides at all. The fallback is passed with
    per-invocation `-c` flags, so it applies to this single commit and writes
    nothing to any system, global or repository gitconfig.
    """
    command = ["git"]

    if not has_usable_git_identity(project_dir):
        command += [
            "-c",
            f"user.name={FALLBACK_COMMITTER_NAME}",
            "-c",
            f"user.email={FALLBACK_COMMITTER_EMAIL}",
        ]

    return command + ["commit", "-m", "Initial scaffold from Forge"]


def run_git_init(project_dir: Path) -> None:
    commands = [
        ["git", "init"],
        ["git", "branch", "-m", "main"],
        ["git", "add", "."],
    ]

    for command in commands:
        run_git_command(project_dir, command)

    # Built after `git init` so repository-local configuration is visible to the
    # identity check.
    run_git_command(project_dir, scaffold_commit_command(project_dir))


def add_remote_origin(project_dir: Path, remote_url: str) -> None:
    run_git_command(project_dir, ["git", "remote", "add", "origin", remote_url])
