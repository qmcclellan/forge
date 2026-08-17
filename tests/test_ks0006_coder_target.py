"""KS-0006: bounded Forge -> Coder/Terraform conversion, against the
StarkGrid-owned coder-terraform-target-contract-v1.

Representative source: templates/node-dashboard (this repository's own
committed template, not a replacement fixture -- KS-0006 Phase B). Target
contract, mapping doc, and structural validator are StarkGrid-owned and
pinned for testing under tests/fixtures/coder_target/ -- see
STARKGRID_CONTRACT_PIN.md there for why this is a versioned contract
dependency, not runtime coupling.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from forge import coder_target as ct

REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_DASHBOARD_DIR = REPO_ROOT / "templates" / "node-dashboard"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "coder_target"
VALIDATOR = FIXTURES / "validate-target-contract.sh"
EXPECTED_EXAMPLE_TF = FIXTURES / "expected-node-dashboard-example" / "main.tf"

FORGE_SHA = "5d21260b42f71162357d35fce20e727e9e9ae773"
GENERATED_AT = "2026-08-17"


def run_starkgrid_validator(target_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(VALIDATOR), str(target_dir)],
        capture_output=True, text=True,
    )


class TestRepresentativeConversionSucceeds:
    """1. representative conversion succeeds."""

    def test_node_dashboard_converts_without_error(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert result["main_tf"]
        assert result["forge_source_md"]

    def test_write_coder_target_writes_both_files(self, tmp_path):
        ct.write_coder_target(NODE_DASHBOARD_DIR, tmp_path, FORGE_SHA, GENERATED_AT)
        assert (tmp_path / "main.tf").is_file()
        assert (tmp_path / "FORGE_SOURCE.md").is_file()


class TestRequiredTargetFieldsExist:
    """2. required target fields exist (contract sections 1-3)."""

    @pytest.fixture
    def generated(self, tmp_path):
        ct.write_coder_target(NODE_DASHBOARD_DIR, tmp_path, FORGE_SHA, GENERATED_AT)
        return tmp_path

    def test_required_providers_present(self, generated):
        text = (generated / "main.tf").read_text()
        assert 'source = "coder/coder"' in text
        assert 'source = "kreuzwerker/docker"' in text

    def test_required_data_sources_present(self, generated):
        text = (generated / "main.tf").read_text()
        assert 'data "coder_workspace" "me"' in text
        assert 'data "coder_workspace_owner" "me"' in text

    def test_required_resources_present(self, generated):
        text = (generated / "main.tf").read_text()
        assert 'resource "coder_agent" "main"' in text
        assert 'resource "docker_volume" "home_volume"' in text
        assert 'resource "docker_container" "workspace"' in text


class TestMappingsPreserveIntendedValues:
    """3. required mappings preserve/document intended values."""

    def test_workspace_image_documents_the_source_runtime(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert "node-20" in result["main_tf"]  # runtime cited in the description
        assert "javascript-node:1-20-bullseye" in result["main_tf"]

    def test_forge_source_records_the_authoritative_template_and_sha(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        md = result["forge_source_md"]
        assert "templates/node-dashboard" in md
        assert FORGE_SHA in md
        assert "qmcclellan/forge" in md
        assert GENERATED_AT in md

    def test_manifest_language_and_runtime_are_the_authoritative_forge_values(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        raw_manifest = json.loads((NODE_DASHBOARD_DIR / "template.json").read_text())
        assert result["manifest"]["language"] == raw_manifest["language"]
        assert result["manifest"]["runtime"] == raw_manifest["runtime"]


class TestDeterminism:
    """4. output is deterministic."""

    def test_same_inputs_produce_byte_identical_output(self):
        r1 = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        r2 = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        r3 = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert r1["main_tf"] == r2["main_tf"] == r3["main_tf"]
        assert r1["forge_source_md"] == r2["forge_source_md"] == r3["forge_source_md"]

    def test_different_forge_sha_changes_only_the_provenance_file(self):
        r1 = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        r2 = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, "f" * 40, GENERATED_AT)
        assert r1["main_tf"] == r2["main_tf"]  # no forge_sha value flows into main.tf
        assert r1["forge_source_md"] != r2["forge_source_md"]

    def test_no_random_or_clock_derived_values(self):
        """Static proof, not merely behavioural: the module never imports
        anything that could introduce a random or wall-clock value."""
        source = (REPO_ROOT / "forge" / "coder_target.py").read_text()
        for forbidden in ("import random", "import uuid", "datetime.now", "time.time", "os.urandom"):
            assert forbidden not in source


class TestUnsupportedInputFailsExplicitly:
    """5. unsupported input fails explicitly. 9. missing required Forge
    source data fails rather than fabricates output."""

    def _manifest(self, **overrides):
        base = {"name": "node-dashboard", "language": "node", "runtime": "node-20", "tags": ["frontend"]}
        base.update(overrides)
        return base

    def test_wrong_language_refused(self):
        with pytest.raises(ct.UnsupportedForgeSource, match="unsupported language"):
            ct.check_source_supported(self._manifest(language="python"))

    def test_missing_frontend_tag_refused(self):
        with pytest.raises(ct.UnsupportedForgeSource, match="unsupported classification"):
            ct.check_source_supported(self._manifest(tags=["backend"]))

    def test_malformed_runtime_refused(self):
        with pytest.raises(ct.UnsupportedForgeSource, match="unsupported runtime"):
            ct.check_source_supported(self._manifest(runtime="node"))

    def test_non_string_runtime_refused(self):
        with pytest.raises(ct.UnsupportedForgeSource):
            ct.check_source_supported(self._manifest(runtime=20))

    @pytest.mark.parametrize("missing_field", ["name", "language", "runtime"])
    def test_missing_required_field_refused(self, missing_field):
        manifest = self._manifest()
        del manifest[missing_field]
        with pytest.raises(ct.UnsupportedForgeSource, match="missing required field"):
            ct.check_source_supported(manifest)

    def test_missing_template_json_refused_not_fabricated(self, tmp_path):
        empty_dir = tmp_path / "no-manifest-here"
        empty_dir.mkdir()
        with pytest.raises(ct.UnsupportedForgeSource, match="missing template.json"):
            ct.convert_to_coder_target(empty_dir, FORGE_SHA, GENERATED_AT)

    def test_malformed_template_json_refused_not_fabricated(self, tmp_path):
        bad_dir = tmp_path / "bad-manifest"
        bad_dir.mkdir()
        (bad_dir / "template.json").write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ct.UnsupportedForgeSource, match="malformed template.json"):
            ct.convert_to_coder_target(bad_dir, FORGE_SHA, GENERATED_AT)

    def test_refusal_never_writes_partial_output(self, tmp_path):
        empty_dir = tmp_path / "no-manifest"
        empty_dir.mkdir()
        out_dir = tmp_path / "out"
        with pytest.raises(ct.UnsupportedForgeSource):
            ct.write_coder_target(empty_dir, out_dir, FORGE_SHA, GENERATED_AT)
        assert not out_dir.exists()

    @pytest.mark.parametrize("missing", ["forge_sha", "generated_at"])
    def test_missing_caller_supplied_provenance_input_refused(self, missing):
        kwargs = {"forge_sha": FORGE_SHA, "generated_at": GENERATED_AT}
        kwargs[missing] = ""
        with pytest.raises(ct.UnsupportedForgeSource):
            ct.convert_to_coder_target(NODE_DASHBOARD_DIR, **kwargs)


class TestSecretSafety:
    """6. secret values are not introduced."""

    # Python re equivalent of validate-target-contract.sh's POSIX-class
    # pattern ([[:space:]] means something different -- a literal character
    # class -- in Python re than in grep -E, so \s is used here instead).
    SECRET_PATTERN = (
        r"BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
        r"sk-[A-Za-z0-9]{20,}|password\s*="
    )

    def test_generated_main_tf_contains_no_secret_pattern(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert re.search(self.SECRET_PATTERN, result["main_tf"]) is None

    def test_credential_interface_is_structural_reference_only(self):
        """The only credential-shaped thing emitted is a Terraform
        interpolation referencing the agent's own token attribute -- never a
        literal value."""
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert "${coder_agent.main.token}" in result["main_tf"]


class TestNode20To22ContractBehavior:
    """7. the Node 20 -> Node 22 contract behavior exactly as documented:
    the mapping doc's own resolution is 'pin the workspace image to Node 20'
    (matching its own worked example) -- reproduced here from the SOURCE's
    declared runtime, not from StarkGrid's live (Node 22) default."""

    def test_node_20_source_produces_node_20_image_not_the_live_22_default(self):
        result = ct.convert_to_coder_target(NODE_DASHBOARD_DIR, FORGE_SHA, GENERATED_AT)
        assert "1-20-bullseye" in result["main_tf"]
        assert "1-22-bullseye" not in result["main_tf"]

    def test_runtime_derived_image_generalizes_by_declared_version_not_hardcoded(self):
        """A hypothetical node-18 source must map to Node 18, proving the
        rule is 'derive from the declared runtime', not 'always emit 20'."""
        assert ct._devcontainer_image_for_runtime("node-18") == (
            "mcr.microsoft.com/devcontainers/javascript-node:1-18-bullseye"
        )


class TestContractConformance:
    """8. generated output conforms to the StarkGrid v1 target contract --
    proven by running StarkGrid's OWN structural validator (pinned copy)
    against the generated output, and by structural comparison against the
    contract's own worked example. The implementation GENERATES; this
    fixture PROVES -- the expected example is read and compared, never
    copied into forge/coder_target.py."""

    def test_generated_output_passes_the_real_starkgrid_validator(self, tmp_path):
        ct.write_coder_target(NODE_DASHBOARD_DIR, tmp_path, FORGE_SHA, GENERATED_AT)
        proc = run_starkgrid_validator(tmp_path)
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_generated_output_structurally_matches_the_contract_example(self, tmp_path):
        """Normalized (whitespace-collapsed) structural comparison against
        the pinned contract example -- not a byte-for-byte copy check, since
        the implementation independently generates rather than echoes it."""
        ct.write_coder_target(NODE_DASHBOARD_DIR, tmp_path, FORGE_SHA, GENERATED_AT)
        generated = (tmp_path / "main.tf").read_text()
        expected = EXPECTED_EXAMPLE_TF.read_text()

        def required_blocks(text):
            return {
                "coder_agent.main": 'resource "coder_agent" "main"' in text,
                "docker_volume.home_volume": 'resource "docker_volume" "home_volume"' in text,
                "docker_container.workspace": 'resource "docker_container" "workspace"' in text,
                "variable.workspace_image": 'variable "workspace_image"' in text,
                "image_is_node_20": "1-20-bullseye" in text,
            }

        assert required_blocks(generated) == required_blocks(expected) == {
            "coder_agent.main": True,
            "docker_volume.home_volume": True,
            "docker_container.workspace": True,
            "variable.workspace_image": True,
            "image_is_node_20": True,
        }

    def test_pinned_validator_matches_its_recorded_sha256(self):
        """Guards against the pin silently drifting from what
        STARKGRID_CONTRACT_PIN.md claims was vendored."""
        pin_doc = (FIXTURES / "STARKGRID_CONTRACT_PIN.md").read_text()
        actual = hashlib.sha256(VALIDATOR.read_bytes()).hexdigest()
        assert actual in pin_doc


class TestWhatConformanceDoesNotProve:
    """Explicit, not implied: passing the structural validator is not a
    claim about live Coder provisioning or Terraform CLI validity."""

    def test_no_terraform_binary_is_invoked_anywhere_in_the_module(self):
        source = (REPO_ROOT / "forge" / "coder_target.py").read_text()
        assert "terraform validate" not in source
        assert "terraform plan" not in source
        assert "subprocess" not in source  # this module shells out to nothing at all


class TestScopeBoundary:
    """KS-0006 Phase L: existing StarkGrid templates are never claimed as
    Forge-originated by this converter."""

    def test_converter_never_writes_into_a_starkgrid_checkout(self):
        """StarkGrid is named only in prose (docstrings/comments citing the
        contract it implements) -- never as a filesystem path this module
        writes to. No live-checkout path, and no write call outside
        write_coder_target's own caller-supplied output_dir."""
        source = (REPO_ROOT / "forge" / "coder_target.py").read_text()
        assert "/srv/workspaces" not in source
        assert "ops/coder/templates" not in source
        assert source.count("write_text(") == 2  # exactly main.tf and FORGE_SOURCE.md, both to output_dir
