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


class GitCommandError(subprocess.CalledProcessError):
    """A failed git command that says what git actually said.

    KS-0044: `subprocess.run(..., check=True)` raises `CalledProcessError`, whose
    message is only "Command '[...]' returned non-zero exit status N." The
    captured stderr lives on the exception but appears nowhere a caller or log
    ever reads, so the real reason -- "Author identity unknown", "remote origin
    already exists" -- was discarded at exactly the moment it was needed.

    Subclassing rather than replacing keeps `returncode`, `cmd`, `output` and
    `stderr` where every existing caller and `except subprocess.CalledProcessError`
    already expects them. Only the rendered message changes.
    """

    def __str__(self) -> str:
        base = super().__str__()
        detail = _git_diagnostic(self.stderr, self.stdout)
        return f"{base}\n{detail}" if detail else base


def _git_diagnostic(stderr: str | None, stdout: str | None) -> str:
    """Git's own words for a failure, preferring stderr and falling back to stdout.

    Most failures land on stderr. Some do not: `git commit` with nothing staged
    exits 1 and writes "nothing to commit" to STDOUT with an empty stderr, so a
    stderr-only fix would still lose the message for that case.
    """
    for stream in (stderr, stdout):
        if stream and stream.strip():
            return stream.strip()
    return ""


def run_git_command(project_dir: Path, command: list[str]) -> None:
    result = subprocess.run(
        command,
        cwd=project_dir,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # check=False plus an explicit raise, rather than check=True, purely so the
    # raised exception can carry git's message. The failure behaviour is
    # otherwise identical: a non-zero return code still raises, and the type is
    # still a CalledProcessError.
    if result.returncode != 0:
        raise GitCommandError(
            returncode=result.returncode,
            cmd=command,
            output=result.stdout,
            stderr=result.stderr,
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
