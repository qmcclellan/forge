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
