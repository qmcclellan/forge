# Forge

Forge is a CLI-first developer-platform tool for creating standardized project lanes with test scaffolding, documentation, Docker/Jenkins readiness, metadata receipts, local environment checks, and project inspection.

## What this demonstrates

Forge demonstrates CLI-first internal developer tooling, repeatable scaffolding, test-backed automation, Docker/Jenkins readiness, Git workflow automation, local environment validation, and public-safe project documentation.

It creates new projects from templates and standardizes:

- folder layout
- README files
- runbooks
- interview/demo documentation
- pytest smoke tests
- optional Git initialization
- optional Docker scaffolding
- optional Jenkins scaffolding

## Goal

Reduce project startup friction and make every new project production-style from day one.

Forge is intended for portfolio projects, internal tooling, and future Friday/Coder workspace workflows.

## Current Features

- forge doctor
- forge project inspect <path>
- generated .forge/project.json metadata receipts
- Java Spring service template
- Node dashboard template
- Nexus-backed template package/publish/pull workflow

- `python-worker` template rendering
- generated README
- generated `.gitignore`
- generated `pyproject.toml`
- generated Python package under `src/`
- generated smoke test under `tests/`
- generated runbook under `docs/`
- generated interview talk track under `docs/`
- `--git-init`
- `--with-docker`
- `--with-jenkins`
- `--remote-url`

## Example

    python3 -m forge.cli new "sre-log-pipeline" \
  --template python-worker \
  --output-dir ./generated-projects \
  --description "A small SRE-style log ingestion pipeline." \
  --with-docker \
  --with-jenkins \
  --git-init \
  --remote-url git@github.com:example/sre-log-pipeline.git

## Local Setup

    cd ./generated-projects/forge
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

## Run Tests

    python -m pytest

Expected:

    28 passed

## Generated Python Worker Usage

Generated `python-worker` projects use a `src/` layout with setuptools package discovery.
Install the generated project before running tests so imports resolve as a normal Python package:

    cd ./generated-projects/sre-log-pipeline
    python -m pip install -e ".[dev]"
    python -m pytest
    python -m sre_log_pipeline.main

## Current Scope

Forge is intentionally small and local-first.

It does not yet:

- create Gitea repositories
- push generated projects to remotes
- create Jenkins jobs
- create Coder workspaces
- manage secrets

## Roadmap

- `--remote-url`
- Gitea push workflow
- generated Jenkins job notes
- Coder/devcontainer templates
- more templates

## Repository

Private Gitea remote:

    git@github.com:example/forge.git

## Artifact publishing

Forge-generated projects can publish Python packages, Docker images, and raw evidence files into the Friday Nexus artifact hub.

See `docs/artifact-publishing.md`.
