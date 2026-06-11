import hashlib
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path


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

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(template_dir, arcname=template)

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
