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
  --output-dir /srv/workspaces/projects/portfolio \
  --description "A small SRE-style log ingestion pipeline." \
  --with-docker \
  --with-jenkins \
  --git-init \
  --remote-url ssh://git@192.168.1.107:2222/portfolio/sre-log-pipeline.git

## Local Setup

    cd /srv/workspaces/projects/portfolio/forge
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install pytest

## Run Tests

    python -m pytest

Expected:

    5 passed

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

    ssh://git@192.168.1.107:2222/portfolio/forge.git
