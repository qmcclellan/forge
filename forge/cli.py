import argparse
import re
from pathlib import Path

from forge.renderer import render_template_dir


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
        default=".",
        help="Directory where the project should be created.",
    )
    new_parser.add_argument(
        "--description",
        default="A generated Forge project.",
        help="Project description.",
    )

    return parser


def create_project(name: str, template: str, output_dir: str, description: str = "A generated Forge project.") -> Path:
    project_slug = slugify(name)
    package_name = package_name_from_slug(project_slug)

    target = Path(output_dir).expanduser().resolve() / project_slug

    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")

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

    target.mkdir(parents=True)
    render_template_dir(template_dir, target, values)

    return target


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "new":
        target = create_project(
            name=args.name,
            template=args.template,
            output_dir=args.output_dir,
            description=args.description,
        )
        print(f"Created project: {target}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
