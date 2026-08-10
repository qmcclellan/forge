import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from forge.cli import build_parser, create_project


def test_parser_exists():
    parser = build_parser()
    assert parser.prog == "forge"


def test_create_project(tmp_path):
    target = create_project(
        name="hello-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A small worker project.",
    )

    assert target.exists()
    assert (target / "README.md").exists()
    assert (target / "pyproject.toml").exists()
    assert (target / "src" / "hello_worker" / "__init__.py").exists()
    assert (target / "src" / "hello_worker" / "main.py").exists()
    assert (target / "tests" / "test_smoke.py").exists()
    assert (target / "docs" / "runbook.md").exists()
    assert (target / "docs" / "interview-talk-track.md").exists()
    assert not (target / "Dockerfile").exists()
    assert not (target / "docker-compose.yml").exists()
    assert not (target / "Jenkinsfile").exists()

    readme = (target / "README.md").read_text()
    pyproject = (target / "pyproject.toml").read_text()
    main_py = (target / "src" / "hello_worker" / "main.py").read_text()

    assert "A small worker project." in readme
    assert 'name = "hello-worker"' in pyproject
    assert "hello-worker is running." in main_py
    assert "[build-system]" in pyproject
    assert "[tool.setuptools.packages.find]" in pyproject
    assert 'where = ["src"]' in pyproject
    assert 'pythonpath = ["src"]' in pyproject


def test_generated_project_smoke_test_runs_with_package_import(tmp_path):
    target = create_project(
        name="package-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker with package imports.",
    )

    generated_test = (target / "tests" / "test_smoke.py").read_text()

    assert "from package_worker.main import main" in generated_test
    assert "from src.package_worker.main" not in generated_test

    subprocess.run(
        # sys.executable, not a bare "python": doctor guarantees only the
        # interpreter already running Forge, and Debian-derived hosts ship no
        # `python` alias. See KS-0016.
        [sys.executable, "-m", "pytest"],
        cwd=target,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_create_project_with_docker(tmp_path):
    target = create_project(
        name="docker-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A Docker-ready worker project.",
        with_docker=True,
    )

    assert (target / "Dockerfile").exists()
    assert (target / "docker-compose.yml").exists()

    dockerfile = (target / "Dockerfile").read_text()
    compose = (target / "docker-compose.yml").read_text()

    assert "FROM python:3.12-slim" in dockerfile
    assert "RUN python -m pip install ." in dockerfile
    assert 'CMD ["python", "-m", "docker_worker.main"]' in dockerfile
    assert "docker-worker" in compose
    assert "python -m docker_worker.main" in compose


def test_create_project_with_jenkins(tmp_path):
    target = create_project(
        name="jenkins-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A Jenkins-ready worker project.",
        with_jenkins=True,
    )

    assert (target / "Jenkinsfile").exists()

    jenkinsfile = (target / "Jenkinsfile").read_text()

    assert "pipeline" in jenkinsfile
    assert 'python -m pip install -e ".[dev]"' in jenkinsfile
    assert "python -m pytest" in jenkinsfile
    assert "jenkins-worker" in jenkinsfile


def test_create_project_with_git_init(tmp_path):
    target = create_project(
        name="git-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker with Git initialized.",
        git_init=True,
    )

    assert (target / ".git").exists()

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()

    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()

    assert branch == "main"
    assert "Initial scaffold from Forge" in log


def test_create_project_with_remote_url_requires_git_init(tmp_path):
    try:
        create_project(
            name="remote-worker",
            template="python-worker",
            output_dir=str(tmp_path),
            description="A worker with a remote URL.",
            remote_url="git@github.com:example/remote-worker.git",
        )
    except ValueError as error:
        assert "--remote-url requires --git-init" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_create_project_with_remote_url(tmp_path):
    remote_url = "git@github.com:example/remote-worker.git"

    target = create_project(
        name="remote-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker with a remote URL.",
        git_init=True,
        remote_url=remote_url,
    )

    configured_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()

    assert configured_remote == remote_url


def test_package_template_creates_archive_and_manifest(tmp_path):
    import json
    import tarfile

    from forge.template_artifacts import package_template

    archive_path, manifest_path = package_template(
        template="python-worker",
        version="0.1.0",
        output_dir=str(tmp_path),
    )

    assert archive_path.exists()
    assert manifest_path.exists()
    assert archive_path.name == "python-worker-0.1.0.tar.gz"
    assert manifest_path.name == "python-worker-0.1.0.manifest.json"

    manifest = json.loads(manifest_path.read_text())

    assert manifest["template"] == "python-worker"
    assert manifest["version"] == "0.1.0"
    assert manifest["archive"] == "python-worker-0.1.0.tar.gz"
    assert manifest["file_count"] > 0
    assert manifest["archive_sha256"]

    paths = {entry["path"] for entry in manifest["files"]}

    assert "README.md.tmpl" in paths
    assert "pyproject.toml.tmpl" in paths
    assert "tests/test_smoke.py.tmpl" in paths

    with tarfile.open(archive_path, "r:gz") as archive:
        names = set(archive.getnames())

    assert "python-worker/README.md.tmpl" in names
    assert "python-worker/pyproject.toml.tmpl" in names


def test_template_artifact_url():
    from forge.template_artifacts import template_artifact_url

    url = template_artifact_url(
        repository_url="http://nexus.example/repository/raw-hosted/",
        template="python-worker",
        version="0.1.0",
        filename="python-worker-0.1.0.tar.gz",
    )

    assert url == "http://nexus.example/repository/raw-hosted/forge/templates/python-worker/0.1.0/python-worker-0.1.0.tar.gz"


def test_template_publish_command_exists():
    parser = build_parser()
    args = parser.parse_args(
        [
            "template",
            "publish",
            "python-worker",
            "--version",
            "0.1.0",
            "--username",
            "admin",
            "--password",
            "secret",
        ]
    )

    assert args.command == "template"
    assert args.template_command == "publish"
    assert args.template == "python-worker"
    assert args.version == "0.1.0"
    assert args.username == "admin"
    assert args.password == "secret"


def test_template_pull_command_exists():
    parser = build_parser()
    args = parser.parse_args(
        [
            "template",
            "pull",
            "python-worker",
            "--version",
            "0.1.0",
            "--username",
            "admin",
            "--password",
            "secret",
            "--cache-dir",
            "/tmp/forge-cache",
        ]
    )

    assert args.command == "template"
    assert args.template_command == "pull"
    assert args.template == "python-worker"
    assert args.version == "0.1.0"
    assert args.username == "admin"
    assert args.password == "secret"
    assert args.cache_dir == "/tmp/forge-cache"



def test_create_project_with_template_dir_override(tmp_path):
    import shutil
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    source_template = repo_root / "templates" / "python-worker"
    copied_template = tmp_path / "copied-python-worker-template"

    shutil.copytree(source_template, copied_template)

    target = create_project(
        name="override-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A project from an override template dir.",
        template_dir_override=str(copied_template),
    )

    assert target.exists()
    assert (target / "README.md").exists()
    assert (target / "pyproject.toml").exists()
    assert (target / "src" / "override_worker" / "__init__.py").exists()
    assert not (target / "Dockerfile").exists()
    assert not (target / "Jenkinsfile").exists()

def test_new_command_accepts_nexus_template_source():
    parser = build_parser()
    args = parser.parse_args(
        [
            "new",
            "nexus-worker",
            "--template",
            "python-worker",
            "--template-source",
            "nexus",
            "--template-version",
            "0.1.0",
            "--template-cache-dir",
            "/tmp/forge-cache",
            "--username",
            "admin",
            "--password",
            "secret",
        ]
    )

    assert args.command == "new"
    assert args.name == "nexus-worker"
    assert args.template == "python-worker"
    assert args.template_source == "nexus"
    assert args.template_version == "0.1.0"
    assert args.template_cache_dir == "/tmp/forge-cache"
    assert args.username == "admin"
    assert args.password == "secret"


def test_template_list_command_exists():
    parser = build_parser()
    args = parser.parse_args(
        [
            "template",
            "list",
            "--source",
            "nexus",
            "--username",
            "admin",
            "--password",
            "secret",
            "--cache-dir",
            "/tmp/forge-cache",
        ]
    )

    assert args.command == "template"
    assert args.template_command == "list"
    assert args.source == "nexus"
    assert args.username == "admin"
    assert args.password == "secret"
    assert args.cache_dir == "/tmp/forge-cache"


def test_package_template_includes_template_metadata(tmp_path):
    import json

    from forge.template_artifacts import package_template

    archive_path, manifest_path = package_template(
        template="python-worker",
        version="0.1.1",
        output_dir=str(tmp_path),
    )

    manifest = json.loads(manifest_path.read_text())

    assert archive_path.exists()
    assert manifest["metadata"]["language"] == "python"
    assert manifest["metadata"]["runtime"] == "python-3.12"
    assert "worker" in manifest["metadata"]["tags"]
    assert manifest["metadata"]["recommended_use"]


def test_template_info_command_exists():
    parser = build_parser()
    args = parser.parse_args(
        [
            "template",
            "info",
            "python-worker",
            "--version",
            "0.1.1",
            "--source",
            "nexus",
            "--username",
            "admin",
            "--password",
            "secret",
            "--cache-dir",
            "/tmp/forge-cache",
        ]
    )

    assert args.command == "template"
    assert args.template_command == "info"
    assert args.template == "python-worker"
    assert args.version == "0.1.1"
    assert args.source == "nexus"
    assert args.username == "admin"
    assert args.password == "secret"
    assert args.cache_dir == "/tmp/forge-cache"


def test_get_nexus_template_info_finds_matching_template(monkeypatch):
    from forge import template_artifacts

    def fake_list_nexus_templates(**kwargs):
        return [
            {
                "template": "python-worker",
                "version": "0.1.1",
                "archive_sha256": "abc123",
                "manifest_url": "http://example/manifest.json",
                "cached": "yes",
                "language": "python",
                "runtime": "python-3.12",
                "description": "A worker template.",
                "recommended_use": "Use for workers.",
                "tags": "python,worker",
            }
        ]

    monkeypatch.setattr(template_artifacts, "list_nexus_templates", fake_list_nexus_templates)

    item = template_artifacts.get_nexus_template_info(
        template="python-worker",
        version="0.1.1",
    )

    assert item["template"] == "python-worker"
    assert item["version"] == "0.1.1"
    assert item["language"] == "python"
    assert item["runtime"] == "python-3.12"


def test_validate_template_structure_passes_for_python_worker():
    from forge.template_artifacts import validate_template_structure

    result = validate_template_structure("python-worker")

    assert result["errors"] == []


def test_validate_template_command_exists():
    parser = build_parser()
    args = parser.parse_args(
        [
            "template",
            "validate",
            "python-worker",
            "--skip-smoke",
        ]
    )

    assert args.command == "template"
    assert args.template_command == "validate"
    assert args.template == "python-worker"
    assert args.skip_smoke is True


def test_create_project_writes_forge_metadata(tmp_path):
    import json

    target = create_project(
        name="metadata-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker with Forge metadata.",
        with_docker=True,
        with_jenkins=True,
    )

    metadata_path = target / ".forge" / "project.json"

    assert metadata_path.exists()

    payload = json.loads(metadata_path.read_text())

    assert payload["project_name"] == "metadata-worker"
    assert payload["template_name"] == "python-worker"
    assert payload["docker_enabled"] is True
    assert payload["jenkins_enabled"] is True
    assert payload["git_initialized"] is False
    assert payload["remote_configured"] is False
    assert payload["forge_version"]
    assert payload["created_at"].endswith("Z")

    serialized = metadata_path.read_text().lower()

    forbidden_values = [
        "/srv/workspaces",
        "192.168.",
        "secret",
        "token",
    ]

    for value in forbidden_values:
        assert value not in serialized


def test_create_project_metadata_tracks_git_and_remote_without_storing_remote_url(tmp_path):
    import json

    remote_url = "git@github.com:example/metadata-remote-worker.git"

    target = create_project(
        name="metadata-remote-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker with Git metadata.",
        git_init=True,
        remote_url=remote_url,
    )

    metadata_path = target / ".forge" / "project.json"
    payload = json.loads(metadata_path.read_text())

    assert payload["git_initialized"] is True
    assert payload["remote_configured"] is True
    assert remote_url not in metadata_path.read_text()


def test_project_inspect_detects_expected_generated_files(tmp_path):
    from forge.project_inspector import inspect_project

    target = create_project(
        name="inspect-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker for inspect testing.",
        with_docker=True,
        with_jenkins=True,
        git_init=True,
        remote_url="git@github.com:example/inspect-worker.git",
    )

    result = inspect_project(target)
    checks = result["checks"]

    assert checks["readme"] is True
    assert checks["runbook"] is True
    assert checks["interview_talk_track"] is True
    assert checks["tests"] is True
    assert checks["pyproject"] is True
    assert checks["dockerfile"] is True
    assert checks["docker_compose"] is True
    assert checks["jenkinsfile"] is True
    assert checks["git_repo"] is True
    assert checks["git_remote"] is True
    assert checks["forge_metadata"] is True


def test_project_inspect_handles_missing_files_without_crashing(tmp_path):
    from forge.project_inspector import inspect_project

    empty_project = tmp_path / "empty-project"
    empty_project.mkdir()

    result = inspect_project(empty_project)
    checks = result["checks"]

    assert checks["readme"] is False
    assert checks["runbook"] is False
    assert checks["interview_talk_track"] is False
    assert checks["tests"] is False
    assert checks["pyproject"] is False
    assert checks["dockerfile"] is False
    assert checks["docker_compose"] is False
    assert checks["jenkinsfile"] is False
    assert checks["git_repo"] is False
    assert checks["git_remote"] is False
    assert checks["forge_metadata"] is False


def test_project_inspect_command_exists():
    parser = build_parser()
    args = parser.parse_args(["project", "inspect", "."])

    assert args.command == "project"
    assert args.project_command == "inspect"
    assert args.path == "."


def test_doctor_runs_and_reports_required_checks():
    from forge.doctor import run_doctor

    result = run_doctor()

    assert "ok" in result
    assert "checks" in result
    assert "python" in result["checks"]
    assert "git" in result["checks"]
    assert "docker" in result["checks"]
    assert "cwd_writable" in result["checks"]
    assert "templates" in result["checks"]
    assert "nexus" in result["checks"]

    assert result["checks"]["python"]["required"] is True
    assert result["checks"]["git"]["required"] is True
    assert result["checks"]["docker"]["required"] is False
    assert result["checks"]["nexus"]["status"] == "skip"


def test_doctor_command_exists():
    parser = build_parser()
    args = parser.parse_args(["doctor"])

    assert args.command == "doctor"
    assert args.json is False


def test_doctor_json_flag_exists():
    parser = build_parser()
    args = parser.parse_args(["doctor", "--json"])

    assert args.command == "doctor"
    assert args.json is True


# --- KS-0004 regression guards ---
# The default Nexus raw URL must not drift back to a pre-migration address.
# These assert the RESOLVED default rather than the source text, so they still
# fail if the constant is correct but a subcommand hardcodes a stale default of
# its own.

PRE_MIGRATION_NEXUS_HOST = "192.168.1.107"
CURRENT_NEXUS_RAW_URL = "http://10.0.0.236:8082/repository/raw-hosted"


def test_default_nexus_raw_url_is_the_current_endpoint():
    from forge.template_artifacts import DEFAULT_NEXUS_RAW_URL

    assert DEFAULT_NEXUS_RAW_URL == CURRENT_NEXUS_RAW_URL
    assert PRE_MIGRATION_NEXUS_HOST not in DEFAULT_NEXUS_RAW_URL


def test_default_nexus_raw_url_derives_a_valid_search_url():
    """The default must stay parseable by the search-URL deriver.

    nexus_search_assets_url() requires '/repository/' and splits the repository
    name off the end. A default that is reachable but shaped wrong would break
    list/info while looking correct.
    """
    from forge.template_artifacts import DEFAULT_NEXUS_RAW_URL, nexus_search_assets_url

    assert (
        nexus_search_assets_url(DEFAULT_NEXUS_RAW_URL)
        == "http://10.0.0.236:8082/service/rest/v1/search/assets?repository=raw-hosted"
    )


def test_every_repository_url_default_resolves_to_the_current_endpoint():
    """All four Nexus subcommands must resolve the same default.

    publish/pull/list/info each declare their own --repository-url default.
    This parses each one and checks the value argparse actually resolves, which
    is exactly what a user gets when they pass no override.
    """
    from forge.template_artifacts import DEFAULT_NEXUS_RAW_URL

    parser = build_parser()
    invocations = [
        ["template", "list"],
        ["template", "info", "python-worker", "--version", "0.1.1"],
        ["template", "publish", "python-worker", "--version", "0.1.1"],
        ["template", "pull", "python-worker", "--version", "0.1.1"],
    ]

    for argv in invocations:
        args = parser.parse_args(argv)
        assert args.repository_url == DEFAULT_NEXUS_RAW_URL, argv
        assert PRE_MIGRATION_NEXUS_HOST not in args.repository_url, argv


def test_repository_url_override_still_wins():
    """Correcting the default must not weaken the explicit flag."""
    parser = build_parser()
    args = parser.parse_args(
        ["template", "list", "--repository-url", "http://nexus.example/repository/raw-hosted"]
    )

    assert args.repository_url == "http://nexus.example/repository/raw-hosted"


# --- KS-0016 regression: nothing may depend on a bare `python` alias ---
# `forge doctor` checks sys.version_info of the interpreter already running
# Forge and never probes PATH for a python executable, so a bare `python` is a
# dependency Forge does not guarantee. Debian-derived hosts do not provide it.

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
# Matches a bare `python` token but not python3 / python3.11 / pythonX.
_BARE_PYTHON = re.compile(r"(?<![\w.-])python(?![\w.-])")


def _shipped_templates():
    return sorted(p for p in _TEMPLATES_DIR.iterdir() if (p / "template.json").is_file())


def test_no_shipped_template_smoke_command_invokes_a_bare_python():
    """Every template's smoke command must run on a python3-only host.

    Checks argv[0] and every argument, so it catches both the direct
    ["python", ...] form and a bare python hidden inside a bash -lc string.
    """
    offenders = []

    for template_dir in _shipped_templates():
        metadata = json.loads((template_dir / "template.json").read_text())
        command = metadata.get("smoke_test_command")
        if not command:
            continue
        assert command[0] != "python", f"{template_dir.name} invokes a bare python directly"
        for part in command:
            if _BARE_PYTHON.search(part):
                offenders.append((template_dir.name, part))

    assert not offenders, f"bare `python` in smoke commands: {offenders}"


def test_default_smoke_command_uses_the_running_interpreter():
    """The fallback for a template shipping no smoke command must not regress."""
    from forge.cli import DEFAULT_SMOKE_TEST_COMMAND

    assert DEFAULT_SMOKE_TEST_COMMAND[0] == sys.executable
    assert DEFAULT_SMOKE_TEST_COMMAND[0] != "python"


def test_python_template_smoke_commands_pass_on_a_python3_only_host(tmp_path):
    """Behavioural guard: run the shipped smoke command against a real project.

    This generates the same project `forge template validate` generates, then
    executes the template's own smoke command in it. It fails on the
    pre-KS-0016 command because that command needs a `python` alias, and it
    fails on any future command that reintroduces an unavailable interpreter.
    """
    for template in ("python-worker", "python-cli"):
        target = create_project(
            name=f"{template}-validate-smoke",
            template=template,
            output_dir=str(tmp_path / template),
            description="Generated by Forge template validation.",
            with_docker=True,
            with_jenkins=True,
        )

        command = json.loads(
            (_TEMPLATES_DIR / template / "template.json").read_text()
        )["smoke_test_command"]

        result = subprocess.run(
            command,
            cwd=target,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        assert result.returncode == 0, f"{template} smoke failed:\n{result.stdout}"


def test_generated_python_projects_still_declare_pytest_for_developers():
    """The smoke command no longer runs pytest, so keep the dev extra honest.

    Dropping pytest from the smoke path must not quietly drop it from the
    generated project's declared dev dependencies.
    """
    for template in ("python-worker", "python-cli"):
        pyproject = (_TEMPLATES_DIR / template / "pyproject.toml.tmpl").read_text()
        assert "pytest" in pyproject, f"{template} no longer declares pytest for developers"


# --- KS-0043 regression: git init must not require an ambient Git identity ---
# A fresh container, CI runner or new workstation has no `git config user.email`.
# Before this fix `forge new --git-init` died on `git commit` with exit 128.
# `no_git_identity` reproduces that: an empty HOME, no system config, and a
# global config pointed at /dev/null.


@pytest.fixture
def no_git_identity(tmp_path, monkeypatch):
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setenv("HOME", str(empty_home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "absent-gitconfig"))
    for leaked in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(leaked, raising=False)
    return empty_home


def _git(project_dir, *args):
    return subprocess.run(
        ["git", *args],
        cwd=project_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_git_init_succeeds_without_any_ambient_identity(tmp_path, no_git_identity):
    """The defect itself: this raised CalledProcessError, exit 128, before the fix."""
    target = create_project(
        name="identityless-worker",
        template="python-worker",
        output_dir=str(tmp_path / "out"),
        description="A worker created where git has no identity.",
        git_init=True,
    )

    assert (target / ".git").exists()

    log = _git(target, "log", "--oneline")
    assert log.returncode == 0, f"no commit was created: {log.stderr}"
    assert "Initial scaffold from Forge" in log.stdout


def test_fallback_identity_is_used_only_when_none_is_available(tmp_path, no_git_identity):
    from forge.git_ops import FALLBACK_COMMITTER_EMAIL, FALLBACK_COMMITTER_NAME

    target = create_project(
        name="fallback-worker",
        template="python-worker",
        output_dir=str(tmp_path / "out"),
        description="A worker created where git has no identity.",
        git_init=True,
    )

    ident = _git(target, "log", "-1", "--format=%an <%ae>|%cn <%ce>")
    author, committer = ident.stdout.strip().split("|")

    expected = f"{FALLBACK_COMMITTER_NAME} <{FALLBACK_COMMITTER_EMAIL}>"
    assert author == expected
    assert committer == expected
    # RFC 2606 reserves .invalid; the fallback must never look contactable.
    assert FALLBACK_COMMITTER_EMAIL.endswith(".invalid")


def test_git_init_writes_no_gitconfig_anywhere(tmp_path, no_git_identity):
    """Forge must supply its identity per-invocation, never by writing config."""
    target = create_project(
        name="noconfig-worker",
        template="python-worker",
        output_dir=str(tmp_path / "out"),
        description="A worker created where git has no identity.",
        git_init=True,
    )

    # Nothing was written into the isolated HOME, and no global config was created.
    assert list(no_git_identity.rglob("*")) == []
    assert not (tmp_path / "absent-gitconfig").exists()

    # And no user.* landed in the generated repository's own config.
    local = _git(target, "config", "--local", "--get-regexp", "^user\\.")
    assert local.stdout.strip() == ""


def test_explicit_user_identity_still_wins(tmp_path, no_git_identity, monkeypatch):
    """A caller-provided identity must not be overridden by the fallback."""
    from forge.git_ops import FALLBACK_COMMITTER_EMAIL

    monkeypatch.setenv("GIT_AUTHOR_NAME", "Real Person")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "real@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Real Person")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "real@example.com")

    target = create_project(
        name="explicit-worker",
        template="python-worker",
        output_dir=str(tmp_path / "out"),
        description="A worker created with an explicit identity.",
        git_init=True,
    )

    ident = _git(target, "log", "-1", "--format=%an <%ae>|%cn <%ce>")
    author, committer = ident.stdout.strip().split("|")

    assert author == "Real Person <real@example.com>"
    assert committer == "Real Person <real@example.com>"
    assert FALLBACK_COMMITTER_EMAIL not in ident.stdout


def test_scaffold_commit_command_carries_no_override_when_identity_exists(
    tmp_path, no_git_identity, monkeypatch
):
    """With an identity available the commit argv must be plain, not `-c` laden.

    The identity is supplied explicitly rather than inherited, so this asserts
    the same thing whether or not the machine running the suite has one.
    """
    from forge.git_ops import scaffold_commit_command

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    # BOTH halves, because a commit needs an author and a committer and they
    # resolve independently. Supplying only one is not a usable identity.
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Real Person")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "real@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Real Person")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "real@example.com")

    command = scaffold_commit_command(repo)

    assert command[:2] == ["git", "commit"], command
    assert "-c" not in command


def test_scaffold_commit_command_adds_the_fallback_when_identity_is_absent(
    tmp_path, no_git_identity
):
    """The mirror case, so the branch is pinned in both directions."""
    from forge.git_ops import FALLBACK_COMMITTER_EMAIL, scaffold_commit_command

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    command = scaffold_commit_command(repo)

    assert "-c" in command
    assert f"user.email={FALLBACK_COMMITTER_EMAIL}" in command
    assert command[-3:] == ["commit", "-m", "Initial scaffold from Forge"]


@pytest.mark.parametrize(
    "half",
    [
        {"GIT_COMMITTER_NAME": "C Person", "GIT_COMMITTER_EMAIL": "c@example.com"},
        {"GIT_AUTHOR_NAME": "A Person", "GIT_AUTHOR_EMAIL": "a@example.com"},
    ],
    ids=["committer-only", "author-only"],
)
def test_git_init_succeeds_when_only_half_an_identity_is_present(
    tmp_path, no_git_identity, monkeypatch, half
):
    """Author and committer identities resolve independently.

    An environment supplying only one half resolves that half and nothing else,
    so a plain commit still fails with exit 128. Checking a single side would
    report a usable identity that does not permit a commit.
    """
    from forge.git_ops import FALLBACK_COMMITTER_EMAIL, FALLBACK_COMMITTER_NAME

    for key, value in half.items():
        monkeypatch.setenv(key, value)

    target = create_project(
        name="half-identity-worker",
        template="python-worker",
        output_dir=str(tmp_path / "out"),
        description="A worker created with only half an identity.",
        git_init=True,
    )

    log = _git(target, "log", "-1", "--format=%an <%ae>|%cn <%ce>")
    assert log.returncode == 0, f"no commit was created: {log.stderr}"

    author, committer = log.stdout.strip().split("|")

    # The half the caller supplied is preserved verbatim; Forge fills only the
    # other half, so the commit can be created at all.
    if "GIT_COMMITTER_EMAIL" in half:
        assert committer == "C Person <c@example.com>"
        assert author == f"{FALLBACK_COMMITTER_NAME} <{FALLBACK_COMMITTER_EMAIL}>"
    else:
        assert author == "A Person <a@example.com>"
        assert committer == f"{FALLBACK_COMMITTER_NAME} <{FALLBACK_COMMITTER_EMAIL}>"


# --- KS-0015 regression: Forge's control file must not become project content ---
# template.json describes the TEMPLATE -- its name, tags, required/optional files
# and smoke command. It was being copied verbatim into every generated project.
# The contract is about that specific control file, NOT about the .json
# extension: legitimate JSON project content must still render normally.


def test_generated_project_does_not_contain_the_template_control_file(tmp_path):
    target = create_project(
        name="control-file-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker that must not carry template metadata.",
    )

    assert not (target / "template.json").exists(), "template control file leaked into the project"


def test_generated_project_still_contains_its_expected_files(tmp_path):
    """The exclusion must remove exactly one file and nothing else."""
    target = create_project(
        name="intact-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="A worker whose real files must survive.",
        with_docker=True,
        with_jenkins=True,
    )

    for expected in (
        "README.md",
        "pyproject.toml",
        "src/intact_worker/main.py",
        "src/intact_worker/__init__.py",
        "tests/test_smoke.py",
        "docs/runbook.md",
        "Dockerfile",
        "docker-compose.yml",
        "Jenkinsfile",
        ".forge/project.json",
    ):
        assert (target / expected).exists(), f"{expected} is missing from the generated project"


def test_no_shipped_template_leaks_its_control_file(tmp_path):
    """Every template, not just the one that happened to be inspected."""
    for template_dir in _shipped_templates():
        name = template_dir.name
        target = create_project(
            name=f"leakcheck-{name}",
            template=name,
            output_dir=str(tmp_path / name),
            description="Leak check.",
        )

        assert not (target / "template.json").exists(), f"{name} leaked its control file"
        # ...and the generation actually produced something.
        assert any(target.rglob("*")), f"{name} produced an empty project"


def test_legitimate_json_project_files_are_still_rendered(tmp_path):
    """The contract is the control file, NOT the .json extension.

    node-api ships package.json.tmpl and docs-control-plane ships
    planning/backlog.schema.json.tmpl. Both must still arrive, rendered.
    """
    api = create_project(
        name="json-api",
        template="node-api",
        output_dir=str(tmp_path / "api"),
        description="An API whose package.json must survive.",
    )
    package_json = api / "package.json"
    assert package_json.exists(), "package.json was not generated"
    # Rendered, not copied raw: the project name substituted into the metadata.
    assert json.loads(package_json.read_text())["name"] == "json-api"

    docs = create_project(
        name="json-docs",
        template="docs-control-plane",
        output_dir=str(tmp_path / "docs"),
        description="A control plane whose schema must survive.",
    )
    schema = docs / "planning" / "backlog.schema.json"
    assert schema.exists(), "backlog.schema.json was not generated"
    json.loads(schema.read_text())


def test_only_the_root_control_file_is_excluded(tmp_path):
    """A nested file named template.json is project content and must render.

    The exclusion matches an exact root-relative path, so a template that ships
    its own template.json below the root is unaffected.
    """
    from forge.renderer import render_template_dir

    template_dir = tmp_path / "fake-template"
    (template_dir / "config").mkdir(parents=True)
    (template_dir / "template.json").write_text('{"name": "fake-template"}')
    (template_dir / "config" / "template.json").write_text('{"kept": "{{ project_name }}"}')

    target = tmp_path / "out"
    render_template_dir(template_dir, target, {"project_name": "Rendered"})

    assert not (target / "template.json").exists(), "root control file should be excluded"
    nested = target / "config" / "template.json"
    assert nested.exists(), "a nested template.json is project content and must be kept"
    assert json.loads(nested.read_text())["kept"] == "Rendered"
