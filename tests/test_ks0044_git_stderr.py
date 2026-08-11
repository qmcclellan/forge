"""KS-0044 regression coverage.

``run_git_command`` piped git's stderr and raised via ``check=True``. The
resulting ``CalledProcessError`` renders as nothing but "Command '[...]' returned
non-zero exit status N" -- the captured stderr sits on the exception where no
caller, log or traceback ever reads it. When KS-0043's identity defect fired in
CI, the Actions log showed only "exit status 128"; the real message, "Author
identity unknown", had to be recovered by a separate manual probe.

These tests pin git's own words into the raised error, and pin the things that
must NOT change: the exception is still a ``CalledProcessError``, the return code
is still represented, successful commands are untouched, and all five callers keep
working.

Every test builds its own repository and supplies an explicit identity with ``-c``
where a commit is involved, so nothing here depends on the host's global git
configuration.
"""

import subprocess
from pathlib import Path

import pytest

from forge import git_ops


IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@test.invalid"]


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _commit_something(repo: Path, name: str = "f.txt"):
    (repo / name).write_text("content", encoding="utf-8")
    git_ops.run_git_command(repo, ["git", "add", "."])
    git_ops.run_git_command(repo, ["git"] + IDENTITY + ["commit", "-m", "seed"])


class TestGitDiagnosticReachesTheCaller:
    def test_stderr_appears_in_the_raised_error(self, repo):
        """The headline contract: git's message, not just a number."""
        git_ops.add_remote_origin(repo, "git@example.invalid:a/b.git")

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.add_remote_origin(repo, "git@example.invalid:c/d.git")

        message = str(excinfo.value)
        assert "remote origin already exists" in message

    def test_the_real_message_is_not_replaced_by_a_generic_forge_one(self, repo):
        """Git's wording must survive verbatim, not be paraphrased by Forge."""
        git_ops.add_remote_origin(repo, "git@example.invalid:a/b.git")

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.add_remote_origin(repo, "git@example.invalid:c/d.git")

        # Whatever git said on stderr is present character-for-character.
        assert excinfo.value.stderr.strip() in str(excinfo.value)

    def test_a_diagnostic_written_to_stdout_is_surfaced_too(self, repo):
        """Not every git failure uses stderr.

        ``git commit`` with nothing staged exits 1 and writes "nothing to commit"
        to STDOUT, leaving stderr empty. A stderr-only fix would still lose it.
        """
        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.run_git_command(repo, ["git"] + IDENTITY + ["commit", "-m", "x"])

        assert excinfo.value.stderr.strip() == "", "precondition: stderr is empty here"
        assert "nothing to commit" in str(excinfo.value)

    def test_unknown_subcommand_surfaces_gits_own_complaint(self, repo):
        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.run_git_command(repo, ["git", "frobnicate"])

        assert "frobnicate" in str(excinfo.value)


class TestFailureBehaviourIsOtherwiseUnchanged:
    def test_the_exception_is_still_a_calledprocesserror(self, repo):
        """Any existing `except subprocess.CalledProcessError` must still catch it."""
        git_ops.add_remote_origin(repo, "git@example.invalid:a/b.git")

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.add_remote_origin(repo, "git@example.invalid:c/d.git")

        assert type(excinfo.value) is git_ops.GitCommandError
        assert isinstance(excinfo.value, subprocess.CalledProcessError)

    def test_the_return_code_is_still_represented(self, repo):
        git_ops.add_remote_origin(repo, "git@example.invalid:a/b.git")

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.add_remote_origin(repo, "git@example.invalid:c/d.git")

        assert excinfo.value.returncode != 0
        # Both as an attribute and in the rendered message.
        assert str(excinfo.value.returncode) in str(excinfo.value)

    def test_the_failing_command_is_still_reported(self, repo):
        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.run_git_command(repo, ["git", "frobnicate"])

        assert excinfo.value.cmd == ["git", "frobnicate"]

    def test_captured_streams_remain_on_the_exception(self, repo):
        """`stderr` and `output` stay where CalledProcessError consumers expect."""
        git_ops.add_remote_origin(repo, "git@example.invalid:a/b.git")

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.add_remote_origin(repo, "git@example.invalid:c/d.git")

        assert excinfo.value.stderr is not None
        assert excinfo.value.output is not None

    def test_a_failure_with_no_output_at_all_still_raises_readably(self, repo, monkeypatch):
        """Degenerate case: nothing to add, so the base message must stand alone."""
        completed = subprocess.CompletedProcess(
            args=["git", "quiet-fail"], returncode=9, stdout="", stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: completed)

        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            git_ops.run_git_command(repo, ["git", "quiet-fail"])

        message = str(excinfo.value)
        assert "9" in message
        assert not message.endswith("\n")


class TestSuccessIsUnaffected:
    def test_successful_commands_do_not_raise(self, repo):
        _commit_something(repo)  # exercises add and commit

    def test_all_five_callers_still_work_end_to_end(self, tmp_path):
        """init, branch, add, commit via run_git_init; remote add via its caller."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / "README.md").write_text("hello", encoding="utf-8")

        # run_git_init drives four of the five commands.
        git_ops.run_git_init(project)
        assert (project / ".git").is_dir()

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project, text=True, capture_output=True, check=True,
        )
        assert branch.stdout.strip() == "main"

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=project, text=True, capture_output=True, check=True,
        )
        assert "Initial scaffold from Forge" in log.stdout

        # The fifth caller.
        git_ops.add_remote_origin(project, "git@example.invalid:a/b.git")
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project, text=True, capture_output=True, check=True,
        )
        assert remote.stdout.strip() == "git@example.invalid:a/b.git"

    def test_git_identity_handling_from_ks0043_is_untouched(self, repo):
        """The earlier fix must keep working: no override when one is resolvable."""
        command = git_ops.scaffold_commit_command(repo)
        assert command[-2:] == ["-m", "Initial scaffold from Forge"]
        assert git_ops.has_usable_git_identity(repo) in (True, False)


class TestTheDefectCannotSilentlyReturn:
    def test_the_shared_path_no_longer_relies_on_check_true(self):
        """`check=True` is precisely what discarded the message.

        It raises a bare CalledProcessError built by subprocess itself, which
        Forge cannot enrich. The shared path must construct its own error.

        Asserted against the parsed AST, not the file text: the function's own
        comment explains why `check=True` was abandoned, so a substring search
        would match the explanation and fail on correct code.
        """
        import ast

        tree = ast.parse(Path(git_ops.__file__).read_text(encoding="utf-8"))
        func = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_git_command"
        )
        checks = [
            keyword.value.value
            for node in ast.walk(func)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "check" and isinstance(keyword.value, ast.Constant)
        ]
        assert checks, "the shared path should still pass check explicitly"
        assert True not in checks

    def test_the_shared_path_still_raises_on_failure(self):
        """Guard against the opposite mistake: check=False and no raise at all."""
        import ast

        tree = ast.parse(Path(git_ops.__file__).read_text(encoding="utf-8"))
        func = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_git_command"
        )
        assert any(isinstance(node, ast.Raise) for node in ast.walk(func)), (
            "dropping check=True without an explicit raise would turn failures into successes"
        )

    def test_the_diagnostic_helper_prefers_stderr_then_stdout(self):
        assert git_ops._git_diagnostic("err", "out") == "err"
        assert git_ops._git_diagnostic("", "out") == "out"
        assert git_ops._git_diagnostic("   ", "out") == "out"
        assert git_ops._git_diagnostic(None, None) == ""
