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
    assert "docker-worker" in compose
    assert "src.docker_worker.main" in compose

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
