import json
import subprocess
from pathlib import Path

import pytest

from forge.cli import create_project
from forge.template_artifacts import validate_template_structure

TEMPLATE = "docs-control-plane"
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "templates" / TEMPLATE

EXISTING_TEMPLATES = [
    "java-batch-job",
    "java-spring-service",
    "node-api",
    "node-dashboard",
    "python-cli",
    "python-worker",
]

REQUIRED_GENERATED_FILES = [
    "README.md",
    "CLAUDE.md",
    "ENGINEERING-METHOD.md",
    "PROJECTS.yaml",
    "NOW.md",
    "MILESTONES.md",
    ".gitignore",
    "docs/runbook.md",
    "planning/backlog.jsonl",
    "planning/backlog.schema.json",
    "planning/dependencies.yaml",
    "planning/decisions/.gitkeep",
    "agents/program-steward.md",
    "agents/project-router.md",
    "agents/backlog-curator.md",
    "agents/session-recorder.md",
    "agents/convergence-analyst.md",
    "agents/delivery-governor.md",
    "workflows/session-start.md",
    "workflows/session-close.md",
    "workflows/idea-intake.md",
    "workflows/milestone-review.md",
    "workflows/cross-project-promotion.md",
    "handoffs/current/.gitkeep",
    "handoffs/archive/.gitkeep",
    "projects/.gitkeep",
    "workspaces/.gitkeep",
]

FORBIDDEN_GENERATED_PATHS = [
    "src",
    "pyproject.toml",
    "package.json",
    "pom.xml",
    "Dockerfile",
    "docker-compose.yml",
    "Jenkinsfile",
    "requirements.txt",
    "build.gradle",
]

# Deliberately narrow: patterns that indicate a real credential, not the word
# "password" appearing in prose about not embedding credentials.
SECRET_PATTERNS = [
    "BEGIN RSA PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN PRIVATE KEY",
    "aws_secret_access_key",
    "ghp_",
    "gho_",
    "xoxb-",
    "AKIA",
]

OPEN_TOKEN = "{" + "{"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Render the template once; reuse across assertions."""
    out = tmp_path_factory.mktemp("docs-control-plane-render")
    return create_project(
        name="Example Control Plane",
        template=TEMPLATE,
        output_dir=str(out),
        description="An example control plane.",
    )


# 1. discoverable ------------------------------------------------------------

def test_template_directory_is_discoverable():
    assert TEMPLATE_DIR.is_dir()
    assert (TEMPLATE_DIR / "template.json").is_file()


def test_template_metadata_is_truthful_about_being_non_runtime():
    metadata = json.loads((TEMPLATE_DIR / "template.json").read_text())
    assert metadata["name"] == TEMPLATE
    assert metadata["language"] == "markdown"
    assert metadata["runtime"] == "none"
    assert metadata["optional_files"] == []


# 2. validation --------------------------------------------------------------

def test_template_structure_validation_succeeds():
    result = validate_template_structure(TEMPLATE)
    assert result["errors"] == []
    assert result["warnings"] == []


# 3 + 4. rendering and required files ----------------------------------------

def test_rendering_succeeds_and_produces_every_required_file(rendered):
    missing = [f for f in REQUIRED_GENERATED_FILES if not (rendered / f).is_file()]
    assert missing == []


# 5 + 6 + 7. no runtime, no manifest, no docker/jenkins ----------------------

@pytest.mark.parametrize("forbidden", FORBIDDEN_GENERATED_PATHS)
def test_no_runtime_or_build_artifacts_are_generated(rendered, forbidden):
    assert not (rendered / forbidden).exists()


def test_no_python_or_node_sources_anywhere_in_output(rendered):
    offenders = [
        str(p.relative_to(rendered))
        for p in rendered.rglob("*")
        if p.is_file() and p.suffix in {".py", ".js", ".jsx", ".java", ".ts"}
    ]
    assert offenders == []


# 8 + 9 + 10. parseable planning contracts -----------------------------------

def _top_level_yaml_keys(text: str) -> set[str]:
    """Keys at column 0. Forge ships no YAML dependency, so this stays stdlib."""
    return {
        line.split(":", 1)[0].strip()
        for line in text.splitlines()
        if line and not line.startswith((" ", "\t", "#")) and ":" in line
    }


def test_projects_yaml_parses(rendered):
    text = (rendered / "PROJECTS.yaml").read_text()

    # YAML forbids tabs for indentation; a tab here would break every parser.
    assert "\t" not in text

    keys = _top_level_yaml_keys(text)
    assert {"registry_version", "control_plane", "access_profiles", "projects"} <= keys
    assert "registry_version: 1" in text
    assert "projects: []" in text
    for profile in ("read_all", "cross_project_design", "single_project_delivery"):
        assert f"{profile}:" in text

    # Stronger check when PyYAML happens to be installed; never required.
    try:
        import yaml
    except ImportError:
        return
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    assert data["registry_version"] == 1
    assert data["projects"] == []
    assert set(data["access_profiles"]) == {
        "read_all",
        "cross_project_design",
        "single_project_delivery",
    }


def test_dependencies_yaml_parses(rendered):
    text = (rendered / "planning" / "dependencies.yaml").read_text()
    assert "\t" not in text
    assert {"dependencies_version", "edges"} <= _top_level_yaml_keys(text)
    assert "edges: []" in text

    try:
        import yaml
    except ImportError:
        return
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    assert data["edges"] == []


def test_backlog_schema_is_valid_json_schema(rendered):
    schema = json.loads((rendered / "planning" / "backlog.schema.json").read_text())

    # Structural JSON Schema checks that need no third-party validator.
    assert schema["$schema"].startswith("https://json-schema.org/draft/")
    assert schema["type"] == "object"
    assert isinstance(schema["properties"], dict)
    assert set(schema["required"]) <= set(schema["properties"])
    for name, spec in schema["properties"].items():
        assert "type" in spec or "enum" in spec, f"property without a type: {name}"
    assert schema["properties"]["bucket"]["enum"] == [
        "now",
        "next",
        "later",
        "evidence_needed",
    ]
    assert schema["additionalProperties"] is False

    # Stronger check when jsonschema happens to be installed; never required.
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.Draft202012Validator.check_schema(schema)


def test_empty_backlog_jsonl_is_valid(rendered):
    raw = (rendered / "planning" / "backlog.jsonl").read_text()
    lines = [line for line in raw.splitlines() if line.strip()]
    assert lines == []
    for line in lines:  # every present line must be a JSON object
        assert isinstance(json.loads(line), dict)


# 11 + 12. workspaces boundary ----------------------------------------------

def test_gitignore_ignores_workspace_contents_but_keeps_the_marker(rendered):
    ignore = (rendered / ".gitignore").read_text()
    assert "workspaces/*" in ignore
    assert "!workspaces/.gitkeep" in ignore


def test_nested_repository_under_workspaces_is_ignored_and_marker_is_trackable(rendered):
    subprocess.run(["git", "init", "-q"], cwd=rendered, check=True)
    nested = rendered / "workspaces" / "some-project"
    (nested / "src").mkdir(parents=True)
    (nested / "src" / "app.py").write_text("print('nested repo content')\n")
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)

    tracked = subprocess.run(
        ["git", "add", "-An", "--dry-run", "."],
        cwd=rendered,
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout

    assert "workspaces/some-project" not in tracked
    assert "workspaces/.gitkeep" in tracked

    ignored = subprocess.run(
        ["git", "check-ignore", "workspaces/some-project/src/app.py"],
        cwd=rendered,
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert ignored.returncode == 0


# 13. truthful receipt -------------------------------------------------------

def test_forge_receipt_is_truthful(rendered):
    receipt = json.loads((rendered / ".forge" / "project.json").read_text())
    assert receipt["template_name"] == TEMPLATE
    assert receipt["docker_enabled"] is False
    assert receipt["jenkins_enabled"] is False
    assert receipt["project_name"] == "example-control-plane"
    assert receipt["created_at"].endswith("Z")


# 14. existing templates untouched ------------------------------------------

@pytest.mark.parametrize("template", EXISTING_TEMPLATES)
def test_existing_templates_remain_valid_and_unchanged(template):
    result = validate_template_structure(template)
    assert result["errors"] == []
    metadata = json.loads((REPO_ROOT / "templates" / template / "template.json").read_text())
    assert metadata["name"] == template
    assert metadata["runtime"] != "none"


# 15. no unresolved template tokens -----------------------------------------

def test_no_unresolved_template_tokens_remain(rendered):
    offenders = [
        str(p.relative_to(rendered))
        for p in rendered.rglob("*")
        if p.is_file() and ".git" not in p.parts and OPEN_TOKEN in p.read_text(errors="ignore")
    ]
    assert offenders == []


def test_template_variables_are_actually_substituted(rendered):
    readme = (rendered / "README.md").read_text()
    assert "Example Control Plane" in readme
    assert "example-control-plane" in readme
    assert "An example control plane." in readme


# 16. secret scan ------------------------------------------------------------

def test_generated_content_contains_no_secret_patterns(rendered):
    offenders = []
    for path in rendered.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern in text:
                offenders.append(f"{path.relative_to(rendered)}:{pattern}")
    assert offenders == []


def test_template_sources_contain_no_secret_patterns():
    offenders = []
    for path in TEMPLATE_DIR.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern in text:
                offenders.append(f"{path.relative_to(TEMPLATE_DIR)}:{pattern}")
    assert offenders == []


# operator TODO contract -----------------------------------------------------

def test_operator_todo_markers_are_present_where_values_are_unknown(rendered):
    """The template must not invent registry values it cannot know."""
    assert "TODO(operator):" in (rendered / "NOW.md").read_text()
    assert "TODO(operator):" in (rendered / "PROJECTS.yaml").read_text()
    assert "TODO(operator):" in (rendered / "MILESTONES.md").read_text()
