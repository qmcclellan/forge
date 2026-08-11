"""KS-0005 regression coverage.

Forge's archival leg defaulted to /mnt/veronica-nfs, a mount layout that was
retired when its duplicate second mount of the same export was removed. The
storage itself was never lost -- it is served at /starkgrid. These tests pin the
corrected defaults, the environment override, and the contracts that must NOT
change: explicit-argument precedence, Nexus independence, and the degraded/skip
behaviour when the destination is unavailable.

None of these require a host mount, elevated privileges, or a real Nexus.
"""

import json
from pathlib import Path

import pytest

from forge import template_artifacts as ta


class TestDefaultsNoLongerReferenceRetiredLayout:
    def test_module_defaults_are_starkgrid_backed(self):
        assert ta.DEFAULT_NFS_BASE == "/starkgrid/devops/nexus/artifacts"
        assert ta.DEFAULT_INGEST_DIR == "/starkgrid/ingest/devops-artifacts"

    def test_retired_mount_path_survives_nowhere_in_the_module(self):
        # The contract is the PATH, not the name. A comment explaining why the
        # path changed is legitimate; the retired path itself must never
        # reappear as a default.
        source = Path(ta.__file__).read_text(encoding="utf-8")
        assert "/mnt/veronica-nfs" not in source

    def test_nexus_url_is_untouched_by_this_change(self):
        # KS-0005 must not disturb the already-migrated Nexus endpoint.
        assert ta.DEFAULT_NEXUS_RAW_URL == "http://10.0.0.236:8082/repository/raw-hosted"


class TestResolutionPrecedence:
    def test_default_when_nothing_supplied(self, monkeypatch):
        monkeypatch.delenv(ta.NFS_BASE_ENV, raising=False)
        monkeypatch.delenv(ta.INGEST_DIR_ENV, raising=False)
        assert ta.resolve_nfs_base() == ta.DEFAULT_NFS_BASE
        assert ta.resolve_ingest_dir() == ta.DEFAULT_INGEST_DIR

    def test_environment_overrides_default(self, monkeypatch):
        monkeypatch.setenv(ta.NFS_BASE_ENV, "/tmp/elsewhere/artifacts")
        monkeypatch.setenv(ta.INGEST_DIR_ENV, "/tmp/elsewhere/ingest")
        assert ta.resolve_nfs_base() == "/tmp/elsewhere/artifacts"
        assert ta.resolve_ingest_dir() == "/tmp/elsewhere/ingest"

    def test_explicit_argument_beats_environment(self, monkeypatch):
        monkeypatch.setenv(ta.NFS_BASE_ENV, "/tmp/from-env")
        monkeypatch.setenv(ta.INGEST_DIR_ENV, "/tmp/from-env-ingest")
        assert ta.resolve_nfs_base("/tmp/explicit") == "/tmp/explicit"
        assert ta.resolve_ingest_dir("/tmp/explicit-ingest") == "/tmp/explicit-ingest"


def _stub_uploads(monkeypatch):
    """Nexus must stay out of these tests entirely."""
    calls = []
    monkeypatch.setattr(ta, "upload_file",
                        lambda path, url, user, pw: calls.append((str(path), url)))
    return calls


class TestArchivalAgainstWritableStandIn:
    """Proves the corrected path is actually used, with no host mount involved."""

    def test_archival_succeeds_and_writes_receipts(self, tmp_path, monkeypatch):
        uploads = _stub_uploads(monkeypatch)
        nfs_base = tmp_path / "artifacts"
        ingest = tmp_path / "ingest"

        result = ta.publish_template(
            template="python-cli",
            version="0.0.1-ks0005",
            username="u",
            password="p",
            output_dir=str(tmp_path / "dist"),
            nfs_base=str(nfs_base),
            ingest_dir=str(ingest),
        )

        assert result["nfs_skipped_reason"] is None, result["nfs_skipped_reason"]

        receipt = Path(result["nfs_receipt"])
        assert receipt.is_file()
        body = receipt.read_text(encoding="utf-8")
        assert "Forge Template Publish Receipt" in body
        assert "nfs_archived" in body

        assert Path(result["ingest_receipt"]).is_file()
        manifest = Path(result["ingest_manifest"])
        assert manifest.is_file()
        json.loads(manifest.read_text(encoding="utf-8"))

        # the retired layout must never be touched
        assert "veronica" not in str(receipt).lower()
        assert str(nfs_base) in str(receipt)

        # Nexus leg ran independently and was not altered
        assert len(uploads) == 2

    def test_environment_override_drives_the_archival_destination(self, tmp_path, monkeypatch):
        _stub_uploads(monkeypatch)
        monkeypatch.setenv(ta.NFS_BASE_ENV, str(tmp_path / "env-artifacts"))
        monkeypatch.setenv(ta.INGEST_DIR_ENV, str(tmp_path / "env-ingest"))

        result = ta.publish_template(
            template="python-cli",
            version="0.0.2-ks0005",
            username="u",
            password="p",
            output_dir=str(tmp_path / "dist"),
        )

        assert result["nfs_skipped_reason"] is None
        assert str(tmp_path / "env-artifacts") in result["nfs_receipt"]


class TestDegradedContractPreserved:
    """The optional/skip behaviour predates KS-0005 and must survive it."""

    def test_unavailable_destination_skips_without_failing_the_publish(self, tmp_path, monkeypatch):
        uploads = _stub_uploads(monkeypatch)
        blocker = tmp_path / "not-a-directory"
        blocker.write_text("this is a file, so mkdir beneath it must fail")

        result = ta.publish_template(
            template="python-cli",
            version="0.0.3-ks0005",
            username="u",
            password="p",
            output_dir=str(tmp_path / "dist"),
            nfs_base=str(blocker / "artifacts"),
            ingest_dir=str(blocker / "ingest"),
        )

        assert result["nfs_skipped_reason"] is not None
        assert "NFS archival skipped" in result["nfs_skipped_reason"]
        assert result["nfs_receipt"] is None

        # Nexus still completed -- the part that matters is independent
        assert len(uploads) == 2
        assert result["archive_url"].startswith(ta.DEFAULT_NEXUS_RAW_URL)
        assert result["archive_sha256"]
