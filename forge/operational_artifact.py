"""Emit a Forge operational-artifact package from Forge's own template validation.

WHY THIS IS FIRST-PARTY FORGE EVIDENCE, which is the whole point of KS-0052.

The package describes Forge validating **Forge's own committed templates** using
Forge's own `validate_template_structure`. Nothing here reads StarkGrid data,
transforms GameQ data, relabels an SRE artifact, or invents a Forge-shaped fixture
to satisfy a milestone. The inputs are `templates/` in this repository and the
outputs are that validator's verdicts, so the artifact is a record of Forge
behaviour over Forge state and nothing else.

Template *validation* was chosen over template *packaging* deliberately.
`package_template` writes a manifest carrying `created_at_utc`, which is
clock-derived and would make a committed artifact non-reproducible; and
`publish_template` mutates Nexus, which must never happen merely to manufacture
evidence. Validation reads committed content and returns verdicts, so the same
tree always yields the same package.

DETERMINISM. Every field is derived from template content. `run_id` is a digest of
the sorted per-template results, so the same tree yields the same run identity and
a changed tree yields a different one -- no clock, no hostname, no path, no
environment. That is what makes the artifact safe to commit and re-verify.

ZERO INCIDENTS IS A VALID PACKAGE, and is the honest outcome when every template
validates. StarkGrid's own artifact contract says a package with no incidents is
legitimate because "registering only failures would make the store a failure log",
and its committed `completed` fixture carries none.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from forge.template_artifacts import validate_template_structure

# The shape StarkGrid's operational ingestion accepts today. Not widened, not
# negotiated: KS-0052 requires using the existing contract or stopping.
INCIDENT_SCHEMA_VERSION = "1.0"
TOOL = "forge"
ADAPTER = "starkgrid"
INCIDENT_EVIDENCE_FILE = "incident-evidence.json"

# One traceId per package is StarkGrid's v1 rule, so a run reporting failures
# across several templates would span workloads and be rejected. Every incident
# emitted here therefore carries the run's single trace.
SERVICE = "forge"
STAGE = "FORGE_TEMPLATE_VALIDATE"
SOURCE_TYPE = "TEMPLATE"


def _templates_root(repo_root: Path) -> Path:
    return repo_root / "templates"


def validate_all(repo_root: Path) -> list[dict]:
    """Run Forge's own validator across every committed template, in sorted order."""
    results = []
    for directory in sorted(p for p in _templates_root(repo_root).iterdir() if p.is_dir()):
        outcome = validate_template_structure(directory.name, template_dir=str(directory))
        results.append({
            "template": directory.name,
            "errors": list(outcome.get("errors", [])),
            "warnings": list(outcome.get("warnings", [])),
        })
    return results


def _run_id(results: list[dict]) -> str:
    """A content-derived run identity.

    Deliberately not a timestamp. A committed artifact whose identity moved every
    time it was regenerated could never be re-verified, and the whole value of
    this package is that StarkGrid can be handed it again and reach the same
    answer.
    """
    seed = json.dumps(results, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "forge-template-validate-" + hashlib.sha256(seed).hexdigest()[:16]


def build_package(repo_root: Path) -> tuple[dict, dict]:
    """Return (incident_evidence, manifest) for the current committed templates."""
    results = validate_all(repo_root)
    run_id = _run_id(results)

    incidents = []
    for result in results:
        for message in result["errors"]:
            incidents.append({
                "service": SERVICE,
                "stage": STAGE,
                "sourceType": SOURCE_TYPE,
                "sourcePath": f"templates/{result['template']}",
                "traceId": run_id,
                "failureCode": "TEMPLATE_STRUCTURE_INVALID",
                "failureAction": "REPORT",
                "occurrences": 1,
                "detail": message,
            })

    incident_evidence = {
        "schemaVersion": INCIDENT_SCHEMA_VERSION,
        "runId": run_id,
        "incidents": incidents,
        "metrics": {
            # Both are the fields StarkGrid's artifact record knows about, and both
            # stay null because Forge measures neither. Coercing null to zero would
            # turn "not measured" into "measured as nothing" in an evidence store.
            "finalKafkaLag": None,
            "manifestCollisionCount": None,
            # Forge's own counts, which are what this run actually measured.
            "templatesValidated": len(results),
            "templatesWithErrors": sum(1 for r in results if r["errors"]),
            "templatesWithWarnings": sum(1 for r in results if r["warnings"]),
        },
    }

    manifest = {
        "tool": TOOL,
        "adapter": ADAPTER,
        "runId": run_id,
        # StarkGrid warns when sourceSlug drifts from the lowercased execution id,
        # and the execution id is taken from incident-evidence runId.
        "sourceSlug": run_id.lower(),
        "incidentEvidenceFile": INCIDENT_EVIDENCE_FILE,
        "incidentSchemaVersion": INCIDENT_SCHEMA_VERSION,
        "incidentCount": len(incidents),
        "normalizedJsonl": "normalized.jsonl",
        "summaryJson": "summary.json",
        "templates": [r["template"] for r in results],
    }
    return incident_evidence, manifest


def canonical_bytes(document: dict) -> bytes:
    """One spelling per document, so the committed bytes and a regeneration match."""
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_package(repo_root: Path, target: Path) -> dict[str, str]:
    incident_evidence, manifest = build_package(repo_root)
    target.mkdir(parents=True, exist_ok=True)

    evidence_bytes = canonical_bytes(incident_evidence)
    (target / INCIDENT_EVIDENCE_FILE).write_bytes(evidence_bytes)
    (target / "manifest.json").write_bytes(canonical_bytes(manifest))

    return {
        "run_id": incident_evidence["runId"],
        "incident_evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "incident_count": str(len(incident_evidence["incidents"])),
    }
