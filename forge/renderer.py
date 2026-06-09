from pathlib import Path


def render_text(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
    return rendered


def render_template_dir(template_dir: Path, target_dir: Path, values: dict[str, str]) -> None:
    for source in template_dir.rglob("*"):
        relative = source.relative_to(template_dir)

        parts = [
            values.get("package_name", part) if part == "__package__" else part
            for part in relative.parts
        ]

        target_relative = Path(*parts)
        if target_relative.suffix == ".tmpl":
            target_relative = target_relative.with_suffix("")

        target = target_dir / target_relative

        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)

        content = source.read_text(encoding="utf-8")
        target.write_text(render_text(content, values), encoding="utf-8")
