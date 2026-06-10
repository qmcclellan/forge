# Forge

Forge is a local project scaffolding CLI for Friday.

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

    8 passed

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

See:

```text
docs/artifact-publishing.md
