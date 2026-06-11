import base64
import hashlib
import gzip
import json
import shutil
import tarfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_NEXUS_RAW_URL = "http://192.168.1.107:8082/repository/raw-hosted"
DEFAULT_NFS_BASE = "/mnt/veronica-nfs/devops/nexus/artifacts"
DEFAULT_INGEST_DIR = "/mnt/veronica-nfs/ingest/devops-artifacts"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_template(
    template: str,
    version: str,
    output_dir: str = "dist/templates",
) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parent.parent
    template_dir = repo_root / "templates" / template

    if not template_dir.exists():
        raise FileNotFoundError(f"Template does not exist: {template}")

    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    archive_path = target_dir / f"{template}-{version}.tar.gz"
    manifest_path = target_dir / f"{template}-{version}.manifest.json"

    with archive_path.open("wb") as raw_handle:
        with gzip.GzipFile(fileobj=raw_handle, mode="wb", mtime=0) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w") as archive:
                for source in sorted(template_dir.rglob("*")):
                    arcname = Path(template) / source.relative_to(template_dir)
                    info = archive.gettarinfo(str(source), arcname=str(arcname))
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""

                    if source.is_file():
                        with source.open("rb") as handle:
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)

    files = []
    for source in sorted(template_dir.rglob("*")):
        if source.is_file():
            relative = source.relative_to(template_dir)
            files.append(
                {
                    "path": str(relative),
                    "size_bytes": source.stat().st_size,
                    "sha256": sha256_file(source),
                }
            )

    manifest = {
        "template": template,
        "version": version,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "archive": archive_path.name,
        "archive_sha256": sha256_file(archive_path),
        "file_count": len(files),
        "files": files,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return archive_path, manifest_path


def template_artifact_url(
    repository_url: str,
    template: str,
    version: str,
    filename: str,
) -> str:
    base = repository_url.rstrip("/")
    return f"{base}/forge/templates/{template}/{version}/{filename}"


def upload_file(
    path: Path,
    url: str,
    username: str,
    password: str,
) -> None:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")

    request = urllib.request.Request(
        url=url,
        data=path.read_bytes(),
        method="PUT",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/octet-stream",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status not in {200, 201, 204}:
            raise RuntimeError(f"Upload failed for {url}: HTTP {response.status}")


def publish_template(
    template: str,
    version: str,
    username: str,
    password: str,
    repository_url: str = DEFAULT_NEXUS_RAW_URL,
    output_dir: str = "dist/templates",
    nfs_base: str = DEFAULT_NFS_BASE,
    ingest_dir: str = DEFAULT_INGEST_DIR,
) -> dict[str, str]:
    archive_path, manifest_path = package_template(
        template=template,
        version=version,
        output_dir=output_dir,
    )

    archive_url = template_artifact_url(
        repository_url=repository_url,
        template=template,
        version=version,
        filename=archive_path.name,
    )
    manifest_url = template_artifact_url(
        repository_url=repository_url,
        template=template,
        version=version,
        filename=manifest_path.name,
    )

    upload_file(archive_path, archive_url, username, password)
    upload_file(manifest_path, manifest_url, username, password)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_sha256 = sha256_file(archive_path)

    nfs_dest = Path(nfs_base).expanduser().resolve() / "forge" / "templates" / template / version
    ingest_dest = Path(ingest_dir).expanduser().resolve()

    nfs_dest.mkdir(parents=True, exist_ok=True)
    ingest_dest.mkdir(parents=True, exist_ok=True)

    shutil.copy2(archive_path, nfs_dest / archive_path.name)
    shutil.copy2(manifest_path, nfs_dest / manifest_path.name)

    receipt_path = nfs_dest / f"publish-receipt-{stamp}.txt"
    receipt = "\n".join(
        [
            "Forge Template Publish Receipt",
            f"timestamp={stamp}",
            f"template={template}",
            f"version={version}",
            f"nexus_url={repository_url.rstrip('/')}/forge/templates/{template}/{version}/",
            f"archive={archive_path.name}",
            f"manifest={manifest_path.name}",
            f"archive_sha256={archive_sha256}",
            "validated=packaged,uploaded_to_nexus,nfs_archived,ingest_receipt_written",
            "",
        ]
    )
    receipt_path.write_text(receipt, encoding="utf-8")

    ingest_receipt = ingest_dest / receipt_path.name
    ingest_manifest = ingest_dest / f"forge-template-{template}-{version}.manifest.json"

    shutil.copy2(receipt_path, ingest_receipt)
    shutil.copy2(manifest_path, ingest_manifest)

    return {
        "archive_path": str(archive_path),
        "manifest_path": str(manifest_path),
        "archive_url": archive_url,
        "manifest_url": manifest_url,
        "nfs_receipt": str(receipt_path),
        "ingest_receipt": str(ingest_receipt),
        "ingest_manifest": str(ingest_manifest),
        "archive_sha256": archive_sha256,
    }
