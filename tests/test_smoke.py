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

    readme = (target / "README.md").read_text()
    pyproject = (target / "pyproject.toml").read_text()
    main_py = (target / "src" / "hello_worker" / "main.py").read_text()

    assert "A small worker project." in readme
    assert 'name = "hello-worker"' in pyproject
    assert "hello-worker is running." in main_py
