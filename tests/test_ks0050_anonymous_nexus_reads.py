"""KS-0050 regression coverage.

Nexus serves this repository's raw content anonymously, and the library layer has
always supported that: ``download_file``, ``download_json``,
``list_nexus_template_assets``, ``list_nexus_templates``, ``get_nexus_template_info``
and ``pull_template`` all take ``username: str | None = None`` and attach an
Authorization header only ``if username and password``.

The CLI could never reach that path. ``--username`` defaulted to a synthetic
``"admin"``, so the username was always truthy, and every Nexus subcommand --
including the read-only ones -- resolved its password as
``args.password or getpass.getpass(...)``. Two consequences, both measured before
the fix: read-only commands demanded credentials they did not need, and in any
non-interactive context the command did not degrade, it CRASHED inside getpass
before a single HTTP request was made.

These tests pin the corrected precedence and, just as importantly, the parts that
must NOT change: explicit credentials still win, bad credentials still fail
loudly, and publishing still requires authentication.

None of these require a live Nexus, a network, or a terminal.
"""

import getpass
from pathlib import Path

import pytest

from forge import cli


ANON = (None, None)


def _forbid_getpass(monkeypatch):
    """Make any getpass call an immediate, obvious test failure.

    This is the heart of the regression: a read must never reach the prompt. A
    monkeypatched raise is used rather than a spy so that an accidental prompt
    cannot be silently absorbed by a caller that ignores the return value.
    """

    def explode(*args, **kwargs):  # pragma: no cover - reaching it IS the failure
        raise AssertionError("getpass was called for an anonymous-capable read")

    monkeypatch.setattr(getpass, "getpass", explode)
    monkeypatch.setattr(cli.getpass, "getpass", explode)


class TestResolverPrecedence:
    """The four-step precedence, asserted directly and in order."""

    def test_explicit_credentials_win(self):
        assert cli.resolve_nexus_credentials(
            "someone", "secret", require_auth=False
        ) == ("someone", "secret")

    def test_explicit_credentials_win_for_writes_too(self):
        assert cli.resolve_nexus_credentials(
            "someone", "secret", require_auth=True
        ) == ("someone", "secret")

    def test_read_without_credentials_is_anonymous(self, monkeypatch):
        _forbid_getpass(monkeypatch)
        assert cli.resolve_nexus_credentials(None, None, require_auth=False) == ANON

    def test_anonymous_read_never_invents_a_username(self, monkeypatch):
        """The specific defect: 'admin' must not be conjured for a read."""
        _forbid_getpass(monkeypatch)
        username, password = cli.resolve_nexus_credentials(
            None, None, require_auth=False
        )
        assert username is None, "an anonymous read must not synthesise a username"
        assert password is None

    def test_a_supplied_username_still_prompts_on_a_terminal(self, monkeypatch):
        """Not every repository is anonymously readable; the prompt still exists."""
        seen = {}

        def fake_getpass(prompt):
            seen["prompt"] = prompt
            return "typed-in"

        monkeypatch.setattr(cli.getpass, "getpass", fake_getpass)
        assert cli.resolve_nexus_credentials(
            "someone", None, require_auth=False, isatty=lambda: True
        ) == ("someone", "typed-in")
        assert "someone" in seen["prompt"]

    def test_write_without_a_password_prompts_on_a_terminal(self, monkeypatch):
        monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "typed-in")
        assert cli.resolve_nexus_credentials(
            "publisher", None, require_auth=True, isatty=lambda: True
        ) == ("publisher", "typed-in")


class TestNonInteractiveNeverBlocks:
    """The exact defect: no prompt when there is no terminal."""

    def test_write_without_credentials_errors_instead_of_prompting(self, monkeypatch):
        _forbid_getpass(monkeypatch)
        with pytest.raises(SystemExit) as excinfo:
            cli.resolve_nexus_credentials(
                "publisher", None, require_auth=True, isatty=lambda: False
            )
        assert "not a terminal" in str(excinfo.value)

    def test_read_with_a_username_but_no_password_errors_and_says_how_to_fix_it(
        self, monkeypatch
    ):
        _forbid_getpass(monkeypatch)
        with pytest.raises(SystemExit) as excinfo:
            cli.resolve_nexus_credentials(
                "someone", None, require_auth=False, isatty=lambda: False
            )
        message = str(excinfo.value)
        assert "not a terminal" in message
        # The escape hatch must be discoverable from the error itself.
        assert "anonymously" in message

    def test_anonymous_read_is_unaffected_by_the_absence_of_a_terminal(
        self, monkeypatch
    ):
        _forbid_getpass(monkeypatch)
        assert cli.resolve_nexus_credentials(
            None, None, require_auth=False, isatty=lambda: False
        ) == ANON


class TestCommandsReachTheAnonymousPath:
    """End-to-end through ``cli.main``, with the network stubbed out.

    Each test asserts on the credentials the CLI *hands to the library*, which is
    the contract that was broken. The stubs stand in for Nexus so the suite stays
    offline.
    """

    def _run(self, monkeypatch, argv):
        monkeypatch.setattr("sys.argv", ["forge"] + argv)
        cli.main()

    def test_list_reads_anonymously(self, monkeypatch, capsys):
        _forbid_getpass(monkeypatch)
        monkeypatch.delenv("NEXUS_USERNAME", raising=False)
        monkeypatch.delenv("NEXUS_PASSWORD", raising=False)
        seen = {}

        def fake_list(*, repository_url, username, password, cache_dir):
            seen["creds"] = (username, password)
            return []

        monkeypatch.setattr(cli, "list_nexus_templates", fake_list)
        self._run(monkeypatch, ["template", "list"])
        assert seen["creds"] == ANON

    def test_info_reads_anonymously(self, monkeypatch, capsys):
        _forbid_getpass(monkeypatch)
        monkeypatch.delenv("NEXUS_USERNAME", raising=False)
        monkeypatch.delenv("NEXUS_PASSWORD", raising=False)
        seen = {}

        def fake_info(*, template, version, repository_url, username, password, cache_dir):
            seen["creds"] = (username, password)
            return {
                "template": template,
                "version": version,
                "language": "node",
                "runtime": "node-20",
                "cached": "no",
                "archive_sha256": "x",
                "manifest_url": "http://nexus/manifest.json",
            }

        monkeypatch.setattr(cli, "get_nexus_template_info", fake_info)
        self._run(monkeypatch, ["template", "info", "node-api", "--version", "0.1.0"])
        assert seen["creds"] == ANON

    def test_pull_reads_anonymously(self, monkeypatch, tmp_path):
        _forbid_getpass(monkeypatch)
        monkeypatch.delenv("NEXUS_USERNAME", raising=False)
        monkeypatch.delenv("NEXUS_PASSWORD", raising=False)
        seen = {}

        def fake_pull(*, template, version, username, password, repository_url, cache_dir):
            seen["creds"] = (username, password)
            return {
                "archive_path": "a",
                "manifest_path": "m",
                "archive_sha256": "s",
                "template_dir": "t",
                "cache_dir": str(cache_dir),
            }

        monkeypatch.setattr(cli, "pull_template", fake_pull)
        self._run(
            monkeypatch,
            ["template", "pull", "node-api", "--version", "0.1.0",
             "--cache-dir", str(tmp_path)],
        )
        assert seen["creds"] == ANON

    def test_explicit_credentials_still_reach_the_library(self, monkeypatch):
        _forbid_getpass(monkeypatch)
        seen = {}

        def fake_list(*, repository_url, username, password, cache_dir):
            seen["creds"] = (username, password)
            return []

        monkeypatch.setattr(cli, "list_nexus_templates", fake_list)
        self._run(
            monkeypatch,
            ["template", "list", "--username", "someone", "--password", "secret"],
        )
        assert seen["creds"] == ("someone", "secret")

    def test_invalid_explicit_credentials_still_surface_the_failure(self, monkeypatch):
        """A bad credential must fail, not silently downgrade to anonymous."""
        _forbid_getpass(monkeypatch)
        from urllib.error import HTTPError

        def fake_list(*, repository_url, username, password, cache_dir):
            assert (username, password) == ("someone", "wrong")
            raise HTTPError("http://nexus/x", 401, "Unauthorized", {}, None)

        monkeypatch.setattr(cli, "list_nexus_templates", fake_list)
        with pytest.raises(HTTPError) as excinfo:
            self._run(
                monkeypatch,
                ["template", "list", "--username", "someone", "--password", "wrong"],
            )
        assert excinfo.value.code == 401


class TestWriteContractUnchanged:
    """Publishing must not have been loosened by any of the above."""

    def test_publish_still_sends_credentials(self, monkeypatch):
        seen = {}

        def fake_publish(*, template, version, username, password, repository_url, output_dir):
            seen["creds"] = (username, password)
            return {
                "archive_path": "a", "manifest_path": "m",
                "archive_url": "u", "manifest_url": "v",
                "archive_sha256": "s", "nfs_skipped_reason": "skipped",
            }

        monkeypatch.setattr(cli, "publish_template", fake_publish)
        monkeypatch.setattr("sys.argv", [
            "forge", "template", "publish", "node-api",
            "--version", "0.1.0", "--username", "publisher", "--password", "secret",
        ])
        cli.main()
        assert seen["creds"] == ("publisher", "secret")

    def test_publish_is_never_downgraded_to_anonymous(self, monkeypatch):
        """require_auth=True must hold even with nothing supplied."""
        with pytest.raises(SystemExit):
            cli.resolve_nexus_credentials(
                None, None, require_auth=True, isatty=lambda: False
            )

    def test_publish_retains_its_admin_username_default(self):
        """Deliberately NOT changed by KS-0050.

        The read commands stopped defaulting to "admin" because that synthetic
        username is what made anonymous reads unreachable. Publishing is a write
        and was already authenticated, so its default is preserved rather than
        altered as a side effect.
        """
        source = Path(cli.__file__).read_text(encoding="utf-8")
        assert source.count('os.environ.get("NEXUS_USERNAME", "admin")') == 1


class TestTheDefectCannotSilentlyReturn:
    def test_no_read_command_resolves_a_password_by_bare_getpass(self):
        """The original one-liner must not reappear anywhere.

        ``args.password or getpass.getpass(...)`` is exactly the construct that
        made every command interactive. Reads and writes both go through the
        resolver now.
        """
        source = Path(cli.__file__).read_text(encoding="utf-8")
        assert "args.password or getpass.getpass" not in source

    def test_every_nexus_command_uses_the_resolver(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        # new(nexus source), publish, pull, list, info
        assert source.count("resolve_nexus_credentials(") == 6  # 5 call sites + the def
