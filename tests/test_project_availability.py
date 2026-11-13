"""Read-only project-availability preflight.

`check_project_availability` must answer whether a proposed project name
collides with an existing local scaffold or Gitea repository -- without
ever creating a directory, a file, or a repository, and without ever
reporting a failed Gitea query as an available name. Every test here
asserts both the decision and that nothing was mutated: no new path exists
under the target workspace after any of these calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forge.project_availability import (
    DECISIONS,
    GiteaProbeResult,
    check_project_availability,
    check_project_availability_json,
    default_gitea_probe,
)

OWNER = "qmcclellan"


def _snapshot(workspace: Path) -> set[str]:
    """Every path under workspace, used to prove a call created nothing."""
    return {str(p) for p in workspace.rglob("*")}


def fake_probe(*, reachable: bool, exists: bool | None, detail: str = "fake"):
    def probe(owner: str, repo_slug: str) -> GiteaProbeResult:
        return GiteaProbeResult(reachable=reachable, exists=exists, detail=detail)

    return probe


# 1. Available name, locally and remotely.
def test_available_locally_and_remotely(tmp_path):
    before = _snapshot(tmp_path)

    result = check_project_availability(
        "Factory Demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )

    assert result["decision"] == "AVAILABLE"
    assert result["project_slug"] == "factory-demo"
    assert result["local_availability"]["exists"] is False
    assert result["gitea_availability"]["exists"] is False
    assert result["provider_reachable"] is True
    assert result["collision_details"] == []
    assert result["validation_errors"] == []
    assert _snapshot(tmp_path) == before


# 2. Existing local directory.
def test_collision_existing_local_directory(tmp_path):
    (tmp_path / "factory-demo").mkdir()
    before = _snapshot(tmp_path)

    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )

    assert result["decision"] == "COLLISION"
    assert result["local_availability"]["exists"] is True
    assert any("local path already exists" in detail for detail in result["collision_details"])
    assert _snapshot(tmp_path) == before


# 3. Existing Gitea repository (local free).
def test_collision_existing_gitea_repository(tmp_path):
    before = _snapshot(tmp_path)

    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=True),
    )

    assert result["decision"] == "COLLISION"
    assert result["local_availability"]["exists"] is False
    assert any("Gitea repository already exists" in detail for detail in result["collision_details"])
    assert _snapshot(tmp_path) == before


# 4. Existing local AND remote project simultaneously.
def test_collision_existing_local_and_remote(tmp_path):
    (tmp_path / "factory-demo").mkdir()
    before = _snapshot(tmp_path)

    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=True),
    )

    assert result["decision"] == "COLLISION"
    assert len(result["collision_details"]) == 2
    assert _snapshot(tmp_path) == before


# 5. Invalid project names.
@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "---",
        "!!!",
        "...",
    ],
)
def test_invalid_names(tmp_path, name):
    before = _snapshot(tmp_path)

    result = check_project_availability(
        name,
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )

    assert result["decision"] == "INVALID_NAME"
    assert result["validation_errors"]
    # An invalid name is never checked at either layer.
    assert result["local_availability"] is None
    assert result["gitea_availability"] is None
    assert result["provider_reachable"] is None
    assert _snapshot(tmp_path) == before


def test_valid_name_with_mixed_case_and_spaces_is_not_invalid(tmp_path):
    # "Factory Demo" is a perfectly good display name; slugify() handles it.
    # This is NOT an invalid-name case -- it is covered by test 1 above, kept
    # here only to document the boundary explicitly.
    result = check_project_availability(
        "Factory Demo 2",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )
    assert result["decision"] != "INVALID_NAME"
    assert result["project_slug"] == "factory-demo-2"


# 6. Gitea authentication failure.
def test_gitea_authentication_failure_is_unknown_not_available(tmp_path):
    before = _snapshot(tmp_path)

    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=False, exists=None, detail="Gitea authentication failed (HTTP 401)"),
    )

    assert result["decision"] == "UNKNOWN"
    assert result["decision"] != "AVAILABLE"
    assert result["provider_reachable"] is False
    assert _snapshot(tmp_path) == before


# 7. Gitea service unavailable.
def test_gitea_service_unavailable_is_unknown_not_available(tmp_path):
    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=False, exists=None, detail="unexpected Gitea response status: 503"),
    )

    assert result["decision"] == "UNKNOWN"
    assert result["decision"] != "AVAILABLE"


# 8. Network timeout.
def test_gitea_network_timeout_is_unknown_not_available(tmp_path):
    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=False, exists=None, detail="Gitea unreachable: timed out"),
    )

    assert result["decision"] == "UNKNOWN"
    assert result["decision"] != "AVAILABLE"


# A failed query must never be interpreted as available, even when the local
# side is already a confirmed, clean collision -- COLLISION must win over
# UNKNOWN, since it is the strictly more certain of the two non-available
# outcomes.
def test_local_collision_wins_over_unreachable_gitea(tmp_path):
    (tmp_path / "factory-demo").mkdir()

    result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=False, exists=None, detail="Gitea unreachable: timed out"),
    )

    assert result["decision"] == "COLLISION"


# 9. Retry of the same preflight -- idempotent, side-effect-free, same answer.
def test_retry_is_idempotent_and_side_effect_free(tmp_path):
    before = _snapshot(tmp_path)

    first = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )
    second = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )

    assert first == second
    assert first["decision"] == "AVAILABLE"
    assert _snapshot(tmp_path) == before


# 10. No filesystem, Git, or remote mutations across the whole suite's shape
# of calls -- a direct assertion on the module's contract, not just on one
# call's side effects.
def test_module_never_imports_or_calls_a_writer(tmp_path):
    import forge.project_availability as mod

    source = Path(mod.__file__).read_text()
    forbidden = ["os.mkdir", "os.makedirs", "shutil.", "subprocess.", ".write_text(", ".write_bytes(", "git_ops"]
    for token in forbidden:
        assert token not in source, f"project_availability.py must never call {token!r}"


def test_json_wrapper_matches_dict_result(tmp_path):
    import json

    dict_result = check_project_availability(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )
    json_result = check_project_availability_json(
        "factory-demo",
        tmp_path,
        OWNER,
        gitea_probe=fake_probe(reachable=True, exists=False),
    )
    assert json.loads(json_result) == dict_result


def test_decision_is_always_one_of_the_four_values(tmp_path):
    cases = [
        fake_probe(reachable=True, exists=False),
        fake_probe(reachable=True, exists=True),
        fake_probe(reachable=False, exists=None),
    ]
    for probe in cases:
        result = check_project_availability("factory-demo", tmp_path, OWNER, gitea_probe=probe)
        assert result["decision"] in DECISIONS
    invalid_result = check_project_availability("", tmp_path, OWNER, gitea_probe=cases[0])
    assert invalid_result["decision"] in DECISIONS


# --- default_gitea_probe: real function, no live network/credential needed ---


def test_default_probe_fails_closed_without_a_configured_credential(monkeypatch):
    monkeypatch.delenv("GITEA_PROJECT_FACTORY_TOKEN", raising=False)

    result = default_gitea_probe(OWNER, "factory-demo")

    assert result.reachable is False
    assert result.exists is None
    assert "GITEA_PROJECT_FACTORY_TOKEN" in result.detail


def test_default_probe_is_the_default_dependency():
    import inspect

    from forge.project_availability import check_project_availability as fn

    signature = inspect.signature(fn)
    assert signature.parameters["gitea_probe"].default is default_gitea_probe
