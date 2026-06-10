# Forge Interview Talk Track

## What Forge Does

Forge is a local project scaffolding CLI for my Friday development node.

It creates new projects from templates and can generate:

- project layout
- README
- runbook
- interview/demo notes
- pytest smoke tests
- Python package structure
- optional Dockerfile
- optional docker-compose.yml
- optional Jenkinsfile
- optional Git initialization with first commit

## Why I Built It

I wanted a repeatable way to start new projects without rebuilding the same folder structure, test setup, documentation, Docker files, and CI scaffolding every time.

The goal was to reduce startup friction and make each project production-style from day one.

## Current Stack

- Python 3
- argparse CLI
- pytest
- Git
- Docker
- Jenkinsfile generation
- Gitea private remote

## Current Features

- CLI help path
- `new` command
- `python-worker` template
- placeholder rendering
- generated Python package
- generated smoke tests
- generated documentation
- `--git-init`
- `--with-docker`
- `--with-jenkins`

## Production-Style Concerns

Forge includes several small but important engineering practices:

- avoids overwriting existing target folders
- renders repeatable project structure
- keeps `.venv` out of Git
- initializes generated repos on `main`
- creates first Git commit automatically when requested
- includes runbooks and interview notes from project creation
- supports Docker packaging
- supports Jenkins pipeline scaffolding
- has pytest coverage for core generation paths

## STAR Story

Situation:
I needed to organize multiple portfolio and infrastructure projects on my Friday development node.

Task:
Create a repeatable scaffolding tool that could standardize new project setup.

Action:
I built a Python CLI with template rendering, smoke tests, documentation generation, optional Git initialization, optional Docker scaffolding, and optional Jenkinsfile generation.

Result:
Forge can now create a new Python worker project that is test-ready, doc-ready, Docker-ready, Jenkins-ready, and Git-initialized from a single command.

## Demo Command

    cd ./generated-projects/forge
    source .venv/bin/activate
    python -m pytest

    rm -rf /tmp/forge-demo/sre-log-pipeline
    python3 -m forge.cli new "sre-log-pipeline" \
      --template python-worker \
      --output-dir /tmp/forge-demo \
      --description "A small SRE-style log ingestion pipeline." \
      --with-docker \
      --with-jenkins \
      --git-init

    cd /tmp/forge-demo/sre-log-pipeline
    python -m pip install -e ".[dev]"
    python -m pytest
    python -m sre_log_pipeline.main
    find . -maxdepth 3 -type f | sort
    git status
    git log --oneline -1

## Interview Summary

Forge is a small DevOps tool I built to standardize how I start projects.

It demonstrates:

- automation mindset
- repeatable workflows
- CI/CD awareness
- documentation discipline
- Git workflow
- Docker packaging
- test-first project setup

It is intentionally small, practical, and extensible.
