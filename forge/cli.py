import argparse
import getpass
import os
import re
import subprocess
import tempfile
from pathlib import Path

from forge.git_ops import add_remote_origin, run_git_init
from forge.project_metadata import write_project_metadata
from forge.renderer import render_template_dir
from forge.template_artifacts import DEFAULT_NEXUS_RAW_URL, package_template, publish_template, pull_template, list_nexus_templates, get_nexus_template_info, validate_template_structure

DEFAULT_PROJECT_ROOT = Path("/srv/workspaces/projects/portfolio/generated-projects")

DEFAULT_TEMPLATE_OUTPUT_DIRS = {
    "python-worker": DEFAULT_PROJECT_ROOT / "backend" / "python",
    "java-spring-service": DEFAULT_PROJECT_ROOT / "backend" / "java",
    "node-dashboard": DEFAULT_PROJECT_ROOT / "frontend" / "node",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def package_name_from_slug(slug: str) -> str:
    return slug.replace("-", "_")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge",
        description="Local project scaffolding CLI for Friday.",
    )

    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new project from a template.",
    )
    new_parser.add_argument("name", help="Project name to create.")
    new_parser.add_argument(
        "--template",
        default="python-worker",
        help="Template name to use.",
    )
    new_parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory where the project should be created. "
            "Defaults to the template lane under "
            "/srv/workspaces/projects/portfolio/generated-projects."
        ),
    )
    new_parser.add_argument(
        "--description",
        default="A generated Forge project.",
        help="Project description.",
    )
    new_parser.add_argument(
        "--git-init",
        action="store_true",
        help="Initialize Git and create the first commit in the generated project.",
    )
    new_parser.add_argument(
        "--with-docker",
        action="store_true",
        help="Include Dockerfile and docker-compose.yml in the generated project.",
    )
    new_parser.add_argument(
        "--with-jenkins",
        action="store_true",
        help="Include a Jenkinsfile in the generated project.",
    )
    new_parser.add_argument(
        "--remote-url",
        default=None,
        help="Set the generated Git repository origin remote URL. Requires --git-init.",
    )
    new_parser.add_argument(
        "--template-source",
        choices=["local", "nexus"],
        default="local",
        help="Template source to use. Defaults to local repo templates.",
    )
    new_parser.add_argument(
        "--template-version",
        default=None,
        help="Template version to use when --template-source nexus is selected.",
    )
    new_parser.add_argument(
        "--template-cache-dir",
        default="~/.forge/templates",
        help="Local template cache directory for Nexus-backed templates.",
    )
    new_parser.add_argument(
        "--repository-url",
        default=DEFAULT_NEXUS_RAW_URL,
        help="Nexus raw-hosted repository URL for Nexus-backed templates.",
    )
    new_parser.add_argument(
        "--username",
        default=os.environ.get("NEXUS_USERNAME", "admin"),
        help="Nexus username for Nexus-backed templates.",
    )
    new_parser.add_argument(
        "--password",
        default=os.environ.get("NEXUS_PASSWORD"),
        help="Nexus password for Nexus-backed templates. Defaults to NEXUS_PASSWORD or prompt.",
    )

    template_parser = subparsers.add_parser(
        "template",
        help="Manage Forge templates.",
    )
    template_subparsers = template_parser.add_subparsers(dest="template_command")

    package_parser = template_subparsers.add_parser(
        "package",
        help="Package a Forge template as a versioned artifact.",
    )
    package_parser.add_argument("template", help="Template name to package.")
    package_parser.add_argument(
        "--version",
        required=True,
        help="Template version to package.",
    )
    package_parser.add_argument(
        "--output-dir",
        default="dist/templates",
        help="Directory where packaged template artifacts should be written.",
    )

    publish_parser = template_subparsers.add_parser(
        "publish",
        help="Package and publish a Forge template to Nexus raw-hosted.",
    )
    publish_parser.add_argument("template", help="Template name to publish.")
    publish_parser.add_argument(
        "--version",
        required=True,
        help="Template version to publish.",
    )
    publish_parser.add_argument(
        "--repository-url",
        default=DEFAULT_NEXUS_RAW_URL,
        help="Nexus raw-hosted repository URL.",
    )
    publish_parser.add_argument(
        "--username",
        default=os.environ.get("NEXUS_USERNAME", "admin"),
        help="Nexus username. Defaults to NEXUS_USERNAME or admin.",
    )
    publish_parser.add_argument(
        "--password",
        default=os.environ.get("NEXUS_PASSWORD"),
        help="Nexus password. Defaults to NEXUS_PASSWORD or prompt.",
    )
    publish_parser.add_argument(
        "--output-dir",
        default="dist/templates",
        help="Directory where packaged template artifacts should be written.",
    )

    pull_parser = template_subparsers.add_parser(
        "pull",
        help="Pull and verify a Forge template from Nexus raw-hosted.",
    )
    pull_parser.add_argument("template", help="Template name to pull.")
    pull_parser.add_argument(
        "--version",
        required=True,
        help="Template version to pull.",
    )
    pull_parser.add_argument(
        "--repository-url",
        default=DEFAULT_NEXUS_RAW_URL,
        help="Nexus raw-hosted repository URL.",
    )
    pull_parser.add_argument(
        "--username",
        default=os.environ.get("NEXUS_USERNAME", "admin"),
        help="Nexus username. Defaults to NEXUS_USERNAME or admin.",
    )
    pull_parser.add_argument(
        "--password",
        default=os.environ.get("NEXUS_PASSWORD"),
        help="Nexus password. Defaults to NEXUS_PASSWORD or prompt.",
    )
    pull_parser.add_argument(
        "--cache-dir",
        default="~/.forge/templates",
        help="Local template cache directory.",
    )

    list_parser = template_subparsers.add_parser(
        "list",
        help="List Forge templates from a registry source.",
    )
    list_parser.add_argument(
        "--source",
        choices=["nexus"],
        default="nexus",
        help="Template registry source to list.",
    )
    list_parser.add_argument(
        "--repository-url",
        default=DEFAULT_NEXUS_RAW_URL,
        help="Nexus raw-hosted repository URL.",
    )
    list_parser.add_argument(
        "--username",
        default=os.environ.get("NEXUS_USERNAME", "admin"),
        help="Nexus username. Defaults to NEXUS_USERNAME or admin.",
    )
    list_parser.add_argument(
        "--password",
        default=os.environ.get("NEXUS_PASSWORD"),
        help="Nexus password. Defaults to NEXUS_PASSWORD or prompt.",
    )
    list_parser.add_argument(
        "--cache-dir",
        default="~/.forge/templates",
        help="Local template cache directory used to report cache status.",
    )

    info_parser = template_subparsers.add_parser(
        "info",
        help="Show detailed information for a Forge template.",
    )
    info_parser.add_argument("template", help="Template name.")
    info_parser.add_argument(
        "--version",
        required=True,
        help="Template version.",
    )
    info_parser.add_argument(
        "--source",
        choices=["nexus"],
        default="nexus",
        help="Template registry source.",
    )
    info_parser.add_argument(
        "--repository-url",
        default=DEFAULT_NEXUS_RAW_URL,
        help="Nexus raw-hosted repository URL.",
    )
    info_parser.add_argument(
        "--username",
        default=os.environ.get("NEXUS_USERNAME", "admin"),
        help="Nexus username. Defaults to NEXUS_USERNAME or admin.",
    )
    info_parser.add_argument(
        "--password",
        default=os.environ.get("NEXUS_PASSWORD"),
        help="Nexus password. Defaults to NEXUS_PASSWORD or prompt.",
    )
    info_parser.add_argument(
        "--cache-dir",
        default="~/.forge/templates",
        help="Local template cache directory used to report cache status.",
    )

    validate_parser = template_subparsers.add_parser(
        "validate",
        help="Validate a local Forge template before publishing.",
    )
    validate_parser.add_argument("template", help="Template name to validate.")
    validate_parser.add_argument(
        "--template-dir",
        default=None,
        help="Optional explicit template directory to validate.",
    )
    validate_parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Only validate template structure; do not render and test a temp project.",
    )

    return parser


def resolve_output_dir(template: str, output_dir: str | None) -> str:
    if output_dir:
        return output_dir

    return str(
        DEFAULT_TEMPLATE_OUTPUT_DIRS.get(
            template,
            DEFAULT_PROJECT_ROOT / "scratch",
        )
    )


def create_project(
    name: str,
    template: str,
    output_dir: str,
    description: str = "A generated Forge project.",
    git_init: bool = False,
    with_docker: bool = False,
    with_jenkins: bool = False,
    remote_url: str | None = None,
    template_dir_override: str | None = None,
) -> Path:
    project_slug = slugify(name)
    package_name = package_name_from_slug(project_slug)

    target = Path(output_dir).expanduser().resolve() / project_slug

    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")

    if template_dir_override:
        template_dir = Path(template_dir_override).expanduser().resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent
        template_dir = repo_root / "templates" / template

    if not template_dir.exists():
        raise FileNotFoundError(f"Template does not exist: {template}")

    values = {
        "project_name": name,
        "project_slug": project_slug,
        "package_name": package_name,
        "description": description,
    }

    optional_files: set[str] = set()
    if with_docker:
        optional_files.update({"Dockerfile.tmpl", "docker-compose.yml.tmpl"})
    if with_jenkins:
        optional_files.add("Jenkinsfile.tmpl")

    target.mkdir(parents=True)
    render_template_dir(
        template_dir=template_dir,
        target_dir=target,
        values=values,
        enabled_optional_files=optional_files,
    )

    if remote_url and not git_init:
        raise ValueError("--remote-url requires --git-init")

    if git_init:
        run_git_init(target)

    if remote_url:
        add_remote_origin(target, remote_url)

    write_project_metadata(
        project_dir=target,
        project_name=project_slug,
        template_name=template,
        docker_enabled=with_docker,
        jenkins_enabled=with_jenkins,
        git_initialized=git_init,
        remote_configured=remote_url is not None,
    )

    return target


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "new":
        template_dir_override = None

        if args.template_source == "nexus":
            if not args.template_version:
                raise ValueError("--template-version is required when --template-source nexus is selected")

            password = args.password or getpass.getpass(f"Nexus password for {args.username}: ")
            pulled = pull_template(
                template=args.template,
                version=args.template_version,
                username=args.username,
                password=password,
                repository_url=args.repository_url,
                cache_dir=args.template_cache_dir,
            )
            template_dir_override = pulled["template_dir"]
            print(f"Using Nexus template: {template_dir_override}")
            print(f"Verified template SHA256: {pulled['archive_sha256']}")

        target = create_project(
            name=args.name,
            template=args.template,
            output_dir=resolve_output_dir(args.template, args.output_dir),
            description=args.description,
            git_init=args.git_init,
            with_docker=args.with_docker,
            with_jenkins=args.with_jenkins,
            remote_url=args.remote_url,
            template_dir_override=template_dir_override,
        )
        print(f"Created project: {target}")
        return

    if args.command == "template" and args.template_command == "package":
        archive_path, manifest_path = package_template(
            template=args.template,
            version=args.version,
            output_dir=args.output_dir,
        )
        print(f"Packaged template archive: {archive_path}")
        print(f"Wrote template manifest: {manifest_path}")
        return

    if args.command == "template" and args.template_command == "publish":
        password = args.password or getpass.getpass(f"Nexus password for {args.username}: ")
        result = publish_template(
            template=args.template,
            version=args.version,
            username=args.username,
            password=password,
            repository_url=args.repository_url,
            output_dir=args.output_dir,
        )
        print(f"Packaged template archive: {result['archive_path']}")
        print(f"Wrote template manifest: {result['manifest_path']}")
        print(f"Uploaded archive: {result['archive_url']}")
        print(f"Uploaded manifest: {result['manifest_url']}")
        print(f"Wrote NFS receipt: {result['nfs_receipt']}")
        print(f"Wrote ingest receipt: {result['ingest_receipt']}")
        print(f"Wrote ingest manifest: {result['ingest_manifest']}")
        print(f"Archive SHA256: {result['archive_sha256']}")
        return

    if args.command == "template" and args.template_command == "pull":
        password = args.password or getpass.getpass(f"Nexus password for {args.username}: ")
        result = pull_template(
            template=args.template,
            version=args.version,
            username=args.username,
            password=password,
            repository_url=args.repository_url,
            cache_dir=args.cache_dir,
        )
        print(f"Downloaded archive: {result['archive_path']}")
        print(f"Downloaded manifest: {result['manifest_path']}")
        print(f"Verified archive SHA256: {result['archive_sha256']}")
        print(f"Extracted template directory: {result['template_dir']}")
        print(f"Template cache directory: {result['cache_dir']}")
        return

    if args.command == "template" and args.template_command == "list":
        password = args.password or getpass.getpass(f"Nexus password for {args.username}: ")
        templates = list_nexus_templates(
            repository_url=args.repository_url,
            username=args.username,
            password=password,
            cache_dir=args.cache_dir,
        )

        if not templates:
            print("No Forge templates found.")
            return

        print("TEMPLATE        VERSION    CACHED    LANGUAGE    RUNTIME       ARCHIVE_SHA256")
        for item in templates:
            print(
                f"{item['template']:<15} "
                f"{item['version']:<10} "
                f"{item['cached']:<8} "
                f"{item.get('language', ''):<11} "
                f"{item.get('runtime', ''):<13} "
                f"{item['archive_sha256']}"
            )
        return

    if args.command == "template" and args.template_command == "info":
        password = args.password or getpass.getpass(f"Nexus password for {args.username}: ")
        item = get_nexus_template_info(
            template=args.template,
            version=args.version,
            repository_url=args.repository_url,
            username=args.username,
            password=password,
            cache_dir=args.cache_dir,
        )

        print(f"Template: {item['template']}")
        print(f"Version: {item['version']}")
        print(f"Language: {item.get('language', '')}")
        print(f"Runtime: {item.get('runtime', '')}")
        print(f"Cached: {item['cached']}")
        print(f"Archive SHA256: {item['archive_sha256']}")
        print(f"Description: {item.get('description', '')}")
        print(f"Tags: {item.get('tags', '')}")
        print(f"Recommended use: {item.get('recommended_use', '')}")
        print(f"Manifest URL: {item['manifest_url']}")
        return

    if args.command == "template" and args.template_command == "validate":
        result = validate_template_structure(
            template=args.template,
            template_dir=args.template_dir,
        )

        for warning in result["warnings"]:
            print(f"WARNING: {warning}")

        if result["errors"]:
            for error in result["errors"]:
                print(f"ERROR: {error}")
            raise SystemExit(1)

        print(f"Template structure valid: {args.template}")

        if not args.skip_smoke:
            with tempfile.TemporaryDirectory(prefix="forge-template-validate-") as temp_dir:
                target = create_project(
                    name=f"{args.template}-validate-smoke",
                    template=args.template,
                    output_dir=temp_dir,
                    description="Generated by Forge template validation.",
                    with_docker=True,
                    with_jenkins=True,
                    template_dir_override=args.template_dir,
                )

                metadata = result.get("metadata", {})
                smoke_command = metadata.get("smoke_test_command", ["python", "-m", "pytest"])

                subprocess.run(
                    smoke_command,
                    cwd=target,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                print(f"Generated smoke project valid: {target}")

        print(f"Template validation passed: {args.template}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
