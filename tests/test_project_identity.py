"""Project identity: human display name vs machine/filesystem slug.

Forge derives the generated directory from the project name. That conflates two
different identities whenever the human-readable name is not already
slug-shaped — "Keystone" cannot produce an `engineering-control-plane`
directory. `--slug` separates them.

Receipt semantics are versioned. Historical unversioned receipts stored the
derived slug in `project_name`; version-2 receipts define `project_name` as the
display name and `project_slug` as the machine identity.
"""

import json

import pytest

from forge.cli import (
    create_project,
    package_name_from_slug,
    slugify,
    validate_slug,
)
from forge.project_metadata import RECEIPT_VERSION

ALL_TEMPLATES = [
    "docs-control-plane",
    "java-batch-job",
    "java-spring-service",
    "node-api",
    "node-dashboard",
    "python-cli",
    "python-worker",
]

# Table-driven invalid slugs: (slug, why it must be rejected)
INVALID_SLUGS = [
    ("", "empty"),
    ("Keystone", "uppercase"),
    ("engineering Control plane", "whitespace"),
    ("engineering\tplane", "tab whitespace"),
    ("engineering/plane", "forward slash"),
    ("engineering\\plane", "backslash"),
    ("../escape", "parent traversal"),
    ("..", "dot-dot"),
    (".", "dot"),
    (".hidden", "leading dot"),
    ("engineering.plane", "embedded dot"),
    ("/absolute/path", "absolute path"),
    ("/", "root"),
    ("-leading-hyphen", "must begin alphanumeric"),
    ("trailing-hyphen-", "must end alphanumeric"),
    ("under_score", "underscore not allowed"),
    ("plus+sign", "symbol not allowed"),
    ("emoji-✨", "non-ascii"),
]

VALID_SLUGS = [
    "engineering-control-plane",
    "keystone",
    "a",
    "a1",
    "1a",
    "0",
    "multi-part-slug-name",
]


# --------------------------------------------------------------------------
# 1 + 2. Omitting --slug preserves existing behaviour exactly
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name,expected_dir",
    [
        ("metadata-worker", "metadata-worker"),   # already slug-shaped
        ("hello-worker", "hello-worker"),
        ("Hello Worker", "hello-worker"),         # historical slugify behaviour
        ("Example Control Plane", "example-control-plane"),
    ],
)
def test_omitting_slug_preserves_directory_behaviour(tmp_path, name, expected_dir):
    target = create_project(
        name=name,
        template="python-worker",
        output_dir=str(tmp_path),
        description="d",
    )
    assert target.name == expected_dir == slugify(name)


def test_slug_shaped_names_remain_behaviourally_compatible(tmp_path):
    """A slug-shaped name yields identical display and machine identities."""
    target = create_project(
        name="metadata-worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="d",
    )
    receipt = json.loads((target / ".forge" / "project.json").read_text())
    assert target.name == "metadata-worker"
    assert receipt["project_name"] == "metadata-worker"
    assert receipt["project_slug"] == "metadata-worker"


# --------------------------------------------------------------------------
# 3 + 4. Explicit --slug controls the directory; docs keep the display name
# --------------------------------------------------------------------------

@pytest.fixture
def keystone(tmp_path):
    return create_project(
        name="Keystone",
        template="docs-control-plane",
        output_dir=str(tmp_path),
        description="Cross-project engineering control plane.",
        slug="engineering-control-plane",
    )


def test_explicit_slug_controls_the_exact_directory(keystone):
    assert keystone.name == "engineering-control-plane"
    assert keystone.is_dir()


def test_rendered_docs_retain_the_display_name(keystone):
    readme = (keystone / "README.md").read_text()
    assert readme.startswith("# Keystone")
    assert "Keystone" in (keystone / "CLAUDE.md").read_text()
    # The slug still reaches templates as {{ project_slug }}.
    assert "engineering-control-plane" in readme


def test_display_name_and_slug_are_both_present_and_distinct(keystone):
    readme = (keystone / "README.md").read_text()
    assert "Keystone" in readme and "engineering-control-plane" in readme


# --------------------------------------------------------------------------
# 5 + 6 + 7. Version-2 receipt records both identities
# --------------------------------------------------------------------------

def test_receipt_version_is_two(keystone):
    receipt = json.loads((keystone / ".forge" / "project.json").read_text())
    assert receipt["receipt_version"] == 2 == RECEIPT_VERSION


def test_receipt_project_name_is_the_display_name(keystone):
    receipt = json.loads((keystone / ".forge" / "project.json").read_text())
    assert receipt["project_name"] == "Keystone"


def test_receipt_project_slug_is_the_effective_slug(keystone):
    receipt = json.loads((keystone / ".forge" / "project.json").read_text())
    assert receipt["project_slug"] == "engineering-control-plane"


def test_receipt_retains_all_pre_existing_fields(keystone):
    """Version 2 is additive: no historical field was dropped."""
    receipt = json.loads((keystone / ".forge" / "project.json").read_text())
    for field in (
        "project_name",
        "template_name",
        "created_at",
        "forge_version",
        "docker_enabled",
        "jenkins_enabled",
        "git_initialized",
        "remote_configured",
    ):
        assert field in receipt, f"version 2 dropped historical field: {field}"
    assert receipt["created_at"].endswith("Z")


# --------------------------------------------------------------------------
# 8. package_name derives from the EFFECTIVE slug
# --------------------------------------------------------------------------

def test_package_name_derives_from_the_explicit_slug(tmp_path):
    target = create_project(
        name="Metadata Worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="d",
        slug="renamed-worker",
    )
    # __package__ is substituted with package_name_from_slug(effective slug),
    # NOT with a package derived from the display name.
    assert (target / "src" / "renamed_worker").is_dir()
    assert not (target / "src" / "metadata_worker").exists()
    assert package_name_from_slug("renamed-worker") == "renamed_worker"


def test_package_name_derives_from_the_implicit_slug(tmp_path):
    target = create_project(
        name="Metadata Worker",
        template="python-worker",
        output_dir=str(tmp_path),
        description="d",
    )
    assert (target / "src" / "metadata_worker").is_dir()


# --------------------------------------------------------------------------
# 9 + 10. Invalid slugs fail BEFORE any filesystem creation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("slug,reason", INVALID_SLUGS, ids=[r for _, r in INVALID_SLUGS])
def test_invalid_explicit_slug_is_rejected(slug, reason):
    with pytest.raises(ValueError):
        validate_slug(slug)


@pytest.mark.parametrize("slug,reason", INVALID_SLUGS, ids=[r for _, r in INVALID_SLUGS])
def test_invalid_slug_creates_nothing_on_disk(tmp_path, slug, reason):
    before = sorted(p.name for p in tmp_path.iterdir())
    with pytest.raises(ValueError):
        create_project(
            name="Keystone",
            template="docs-control-plane",
            output_dir=str(tmp_path),
            description="d",
            slug=slug,
        )
    after = sorted(p.name for p in tmp_path.iterdir())
    assert after == before == [], f"{reason}: filesystem was touched before validation"


@pytest.mark.parametrize("slug", VALID_SLUGS)
def test_valid_slugs_are_accepted_unchanged(slug):
    """A valid explicit slug is returned verbatim — never normalized."""
    assert validate_slug(slug) == slug


def test_explicit_slug_is_not_silently_normalized(tmp_path):
    """An uppercase slug is an error, not something quietly lowercased."""
    with pytest.raises(ValueError) as excinfo:
        create_project(
            name="Keystone",
            template="docs-control-plane",
            output_dir=str(tmp_path),
            description="d",
            slug="Engineering-Control-Plane",
        )
    assert "lowercase" in str(excinfo.value)
    assert not (tmp_path / "engineering-control-plane").exists()
    assert not (tmp_path / "Engineering-Control-Plane").exists()


# --------------------------------------------------------------------------
# 11. Existing-target protection still applies to explicit slugs
# --------------------------------------------------------------------------

def test_existing_target_protection_with_explicit_slug(tmp_path):
    (tmp_path / "engineering-control-plane").mkdir()
    with pytest.raises(FileExistsError):
        create_project(
            name="Keystone",
            template="docs-control-plane",
            output_dir=str(tmp_path),
            description="d",
            slug="engineering-control-plane",
        )


def test_existing_target_protection_without_slug(tmp_path):
    (tmp_path / "hello-worker").mkdir()
    with pytest.raises(FileExistsError):
        create_project(
            name="Hello Worker",
            template="python-worker",
            output_dir=str(tmp_path),
            description="d",
        )


# --------------------------------------------------------------------------
# 12. Every template renders under both identity modes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_every_template_renders_with_an_explicit_slug(tmp_path, template):
    target = create_project(
        name="Identity Probe",
        template=template,
        output_dir=str(tmp_path),
        description="d",
        slug="identity-probe-renamed",
    )
    assert target.name == "identity-probe-renamed"
    assert (target / "README.md").is_file()
    receipt = json.loads((target / ".forge" / "project.json").read_text())
    assert receipt["project_name"] == "Identity Probe"
    assert receipt["project_slug"] == "identity-probe-renamed"
    assert receipt["template_name"] == template


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_every_template_renders_without_a_slug(tmp_path, template):
    target = create_project(
        name="Identity Probe",
        template=template,
        output_dir=str(tmp_path),
        description="d",
    )
    assert target.name == "identity-probe"


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------

def test_new_command_exposes_slug_argument():
    from forge.cli import build_parser

    args = build_parser().parse_args(
        ["new", "Keystone", "--slug", "engineering-control-plane"]
    )
    assert args.slug == "engineering-control-plane"
    assert args.name == "Keystone"


def test_new_command_slug_defaults_to_none():
    from forge.cli import build_parser

    args = build_parser().parse_args(["new", "Keystone"])
    assert args.slug is None
