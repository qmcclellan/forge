# Forge Runbook

## Purpose

Forge is a CLI-first developer-platform tool for creating standardized project lanes.

It creates new projects from reusable templates and can optionally add Git, Docker, and Jenkins scaffolding.

## Local Setup

Run:

    cd forge
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

## Run Tests

Run:

    python -m pytest

Expected result:

    28 passed

## Basic CLI Smoke Test

Run:

    rm -rf /tmp/forge-test/hello-worker
    python3 -m forge.cli new "hello-worker" \
      --template python-worker \
      --output-dir /tmp/forge-test \
      --description "A generated worker used to test Forge."

Expected files:

    /tmp/forge-test/hello-worker/README.md
    /tmp/forge-test/hello-worker/pyproject.toml
    /tmp/forge-test/hello-worker/src/hello_worker/main.py
    /tmp/forge-test/hello-worker/tests/test_smoke.py
    /tmp/forge-test/hello-worker/docs/runbook.md
    /tmp/forge-test/hello-worker/docs/interview-talk-track.md

Optional generated project package smoke test:

    cd /tmp/forge-test/hello-worker
    python -m pip install -e ".[dev]"
    python -m pytest
    python -m hello_worker.main

Inspect generated project:

    forge project inspect /tmp/forge-test/hello-worker
    cat /tmp/forge-test/hello-worker/.forge/project.json


    
## Doctor Smoke Test

Run:

    forge doctor
    forge doctor --json

Expected:

    required checks report ok
    Nexus reports skip unless configured



## Git Init Smoke Test

Run:

    rm -rf /tmp/forge-test/git-worker
    python3 -m forge.cli new "git-worker" \
      --template python-worker \
      --output-dir /tmp/forge-test \
      --description "A generated worker with Git initialized." \
      --git-init

Verify:

    cd /tmp/forge-test/git-worker
    git status
    git branch --show-current
    git log --oneline -1

Expected:

    On branch main
    nothing to commit, working tree clean
    main
    Initial scaffold from Forge

## Docker Smoke Test

Run:

    rm -rf /tmp/forge-test/docker-worker
    python3 -m forge.cli new "docker-worker" \
      --template python-worker \
      --output-dir /tmp/forge-test \
      --description "A generated Docker-ready worker." \
      --with-docker

Verify:

    cat /tmp/forge-test/docker-worker/Dockerfile
    cat /tmp/forge-test/docker-worker/docker-compose.yml

Optional runtime check:

    cd /tmp/forge-test/docker-worker
    docker compose up --build
    docker compose down

Expected output:

    docker-worker is running.

## Jenkins Smoke Test

Run:

    rm -rf /tmp/forge-test/jenkins-worker
    python3 -m forge.cli new "jenkins-worker" \
      --template python-worker \
      --output-dir /tmp/forge-test \
      --description "A generated Jenkins-ready worker." \
      --with-docker \
      --with-jenkins \
      --git-init

Verify:

    cd /tmp/forge-test/jenkins-worker
    cat Jenkinsfile
    git status
    git log --oneline -1

Expected generated files:

    Dockerfile
    docker-compose.yml
    Jenkinsfile

Expected Git state:

    On branch main
    nothing to commit, working tree clean

## Current Status

Forge currently has:

- a working CLI help path
- a working `new` command
- python-worker template rendering
- optional Git initialization
- optional Docker scaffolding
- optional Jenkins scaffolding
- pytest smoke coverage
- private Gitea remote under `portfolio/forge`
- `.forge/project.json` metadata receipts
- `forge doctor`
- `forge project inspect <path>`

