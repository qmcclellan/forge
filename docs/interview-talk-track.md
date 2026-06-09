# Forge Interview Talk Track

## What Forge Does

Forge is a local project scaffolding CLI for my Friday development node. It creates new projects from templates and standardizes project layout, documentation, test setup, and future CI/CD integration.

## Why I Built It

I wanted a repeatable way to start new projects without rebuilding the same folder structure, README, runbook, test setup, and automation hooks every time.

## Current Stack

- Python 3
- argparse CLI
- pytest smoke tests
- Git-based workflow
- Friday development node

## Current Features

- CLI help path
- `new` command
- project folder creation
- generated README
- smoke tests
- documented runbook

## Production-Style Concerns

- avoids overwriting existing target folders
- keeps virtual environment out of Git
- documents local setup and smoke testing
- separates portfolio project work from platform service data

## STAR Story

Situation:
I needed to organize multiple portfolio and infrastructure projects on my Friday development node.

Task:
Create a repeatable scaffolding tool that could standardize new project setup.

Action:
I built a Python CLI with a `new` command, added smoke tests, documented the runbook, and committed the project in small clean Git checkpoints.

Result:
Forge can now create a basic project folder and README, and it has a passing test suite with a clean Git history.

## Demo Command

    cd /srv/workspaces/projects/portfolio/forge
    source .venv/bin/activate
    python -m pytest
    python3 -m forge.cli new hello-worker --template python-worker --output-dir /tmp/forge-test

