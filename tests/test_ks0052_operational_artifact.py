"""KS-0052: Forge emits a first-party operational-artifact package.

The properties that matter are that the artifact is genuinely Forge-originated,
that it is reproducible from the committed tree, and that nothing host-local leaks
into evidence that will be committed and later re-verified.

These are Forge-side tests only. They are NOT the spanning proof -- that requires
StarkGrid actually ingesting and returning the package, and it is recorded
separately.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from forge import operational_artifact as oa

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED = REPO_ROOT / "evidence" / "operational"


class TestArtifactIsForgeOriginated:
    def test_it_is_built_from_forge_templates_and_nothing_else(self):
        """Every input is a directory under this repository's templates/."""
        results = oa.validate_all(REPO_ROOT)
        committed = sorted(p.name for p in (REPO_ROOT / "templates").iterdir() if p.is_dir())
        assert [r["template"] for r in results] == committed
        assert results, "Forge must have templates to validate"

    def test_it_reports_forge_as_the_producing_tool(self):
        _, manifest = oa.build_package(REPO_ROOT)
        assert manifest["tool"] == "forge"

    def test_incidents_when_present_describe_forge_templates(self):
        evidence, _ = oa.build_package(REPO_ROOT)
        for incident in evidence["incidents"]:
            assert incident["service"] == "forge"
            assert incident["sourcePath"].startswith("templates/")

    def test_no_foreign_source_vocabulary_appears(self):
        """Guards the KS-M4 trap: this must not be another project's data relabelled."""
        blob = json.dumps(oa.build_package(REPO_ROOT)).lower()
        for foreign in ("gameq", "sre-log-pipeline", "digplate", "argus", "moonlight"):
            assert foreign not in blob, f"{foreign!r} has no business in a Forge-origin artifact"


class TestDeterminism:
    def test_two_builds_of_the_same_tree_are_identical(self):
        assert oa.build_package(REPO_ROOT) == oa.build_package(REPO_ROOT)

    def test_the_run_id_is_content_derived_not_a_clock(self):
        evidence, _ = oa.build_package(REPO_ROOT)
        assert re.fullmatch(r"forge-template-validate-[0-9a-f]{16}", evidence["runId"])

    def test_a_changed_template_changes_the_run_id(self, tmp_path):
        """Identity must track content, or a committed artifact cannot be re-verified."""
        import shutil
        clone = tmp_path / "forge"
        shutil.copytree(REPO_ROOT / "templates", clone / "templates")
        before = oa._run_id(oa.validate_all(clone))
        (clone / "templates" / "python-cli" / "template.json").unlink()
        after = oa._run_id(oa.validate_all(clone))
        assert before != after

    def test_the_committed_package_matches_a_fresh_regeneration(self):
        """The committed bytes are reproducible, not a one-off snapshot."""
        evidence, manifest = oa.build_package(REPO_ROOT)
        assert (COMMITTED / "incident-evidence.json").read_bytes() == oa.canonical_bytes(evidence)
        assert (COMMITTED / "manifest.json").read_bytes() == oa.canonical_bytes(manifest)


class TestPackageConformsToTheIngestionContract:
    """The fields StarkGrid's operational path requires today. Contract not widened."""

    def test_incident_evidence_carries_its_required_fields(self):
        evidence, _ = oa.build_package(REPO_ROOT)
        for field in ("schemaVersion", "runId", "incidents", "metrics"):
            assert field in evidence
        assert isinstance(evidence["metrics"], dict)

    def test_manifest_carries_its_required_fields(self):
        _, manifest = oa.build_package(REPO_ROOT)
        for field in ("tool", "runId", "sourceSlug", "adapter",
                      "incidentEvidenceFile", "incidentSchemaVersion", "incidentCount"):
            assert field in manifest

    def test_manifest_and_evidence_agree(self):
        evidence, manifest = oa.build_package(REPO_ROOT)
        assert manifest["runId"] == evidence["runId"]
        assert manifest["incidentCount"] == len(evidence["incidents"])
        assert manifest["incidentSchemaVersion"] == evidence["schemaVersion"]
        assert manifest["incidentEvidenceFile"] == "incident-evidence.json"

    def test_source_slug_matches_the_execution_id(self):
        """StarkGrid warns when these drift; agreeing keeps the run warning-free."""
        evidence, manifest = oa.build_package(REPO_ROOT)
        assert manifest["sourceSlug"] == evidence["runId"].lower()

    def test_all_incidents_share_one_trace(self):
        """One workload per package is StarkGrid's v1 rule."""
        evidence, _ = oa.build_package(REPO_ROOT)
        assert len({i["traceId"] for i in evidence["incidents"]}) <= 1

    def test_zero_incidents_is_a_legitimate_package(self):
        evidence, manifest = oa.build_package(REPO_ROOT)
        if evidence["incidents"]:
            pytest.skip("templates currently report errors; the clean case is covered elsewhere")
        assert manifest["incidentCount"] == 0


class TestCommittedEvidenceIsSafe:
    """Nothing host-local, transient or secret may enter committed evidence."""

    def _committed_text(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(COMMITTED.glob("*.json")))

    def test_no_absolute_or_host_paths(self):
        text = self._committed_text()
        for fragment in ("/home/", "/srv/", "/tmp/", "/root/", "/mnt/", "C:\\"):
            assert fragment not in text

    def test_no_hostname_or_user_leaks(self):
        text = self._committed_text().lower()
        for fragment in ("friday", "station12", "ultron", "que@", "localhost"):
            assert fragment not in text

    def test_no_credential_shaped_content(self):
        text = self._committed_text().lower()
        for fragment in ("password", "secret", "token", "api_key", "authorization", "ssh-rsa"):
            assert fragment not in text

    def test_no_timestamp_or_other_transient_field(self):
        """A clock-derived field would make the committed artifact irreproducible."""
        text = self._committed_text()
        assert "created_at" not in text
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text)

    def test_the_package_is_exactly_two_files(self):
        assert sorted(p.name for p in COMMITTED.glob("*")) == [
            "incident-evidence.json", "manifest.json"]
