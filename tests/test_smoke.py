import subprocess

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
        ["python", "-m", "pytest"],
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
