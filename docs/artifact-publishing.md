# Artifact Publishing with Friday Nexus

Forge-generated projects can be built, tested, packaged, and published into the Friday Nexus artifact hub.

## Friday artifact hub

Nexus runs on Friday:

- Nexus UI: http://192.168.1.107:8082
- Docker registry: 192.168.1.107:5000
- PyPI hosted: http://192.168.1.107:8082/repository/pypi-hosted/
- Raw hosted: http://192.168.1.107:8082/repository/raw-hosted/

## Validated repositories

- raw-hosted: Raw evidence files, logs, release bundles, reports, and smoke-test artifacts.
- pypi-hosted: Python wheels and source distributions.
- docker-hosted: Docker/OCI images.

## Build and publish a Python package

From a Forge-generated Python project:

    cd /srv/workspaces/projects/portfolio/<project-name>
    source .venv/bin/activate

    python -m pip install -U pip
    python -m pip install -e ".[dev]"
    python -m pytest

    python -m pip install build twine
    python -m build

Expected output:

    dist/
      <package-name>-0.1.0.tar.gz
      <package-name>-0.1.0-py3-none-any.whl

Upload to Friday Nexus:

    python -m twine upload \
      --repository-url http://192.168.1.107:8082/repository/pypi-hosted/ \
      -u admin \
      dist/*

## Install a Python package from Friday Nexus

Use a clean virtual environment:

    rm -rf /tmp/nexus-pypi-check
    mkdir -p /tmp/nexus-pypi-check
    cd /tmp/nexus-pypi-check

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -U pip

Install from Nexus:

    python -m pip install \
      --index-url http://192.168.1.107:8082/repository/pypi-hosted/simple/ \
      --trusted-host 192.168.1.107 \
      <package-name>

Run the package:

    python -m <package_name>.main

## Publish a Docker image

Friday Docker is configured to trust the local Nexus Docker registry:

    192.168.1.107:5000

Build, tag, and push:

    docker build -t <project-name>:local .
    docker tag <project-name>:local 192.168.1.107:5000/forge/<project-name>:0.1.0
    docker push 192.168.1.107:5000/forge/<project-name>:0.1.0

Pull back from Nexus:

    docker pull 192.168.1.107:5000/forge/<project-name>:0.1.0

## Upload raw evidence

Use raw-hosted for logs, reports, benchmark summaries, release notes, and other files that should be archived or made searchable later.

    echo "Forge artifact hub smoke test - $(date -u)" > /tmp/forge-nexus-smoke.txt

    curl -u admin \
      --upload-file /tmp/forge-nexus-smoke.txt \
      http://192.168.1.107:8082/repository/raw-hosted/forge/smoke/forge-nexus-smoke.txt

Download it back:

    curl -u admin \
      http://192.168.1.107:8082/repository/raw-hosted/forge/smoke/forge-nexus-smoke.txt

## Validated smoke tests

The Friday Nexus artifact hub has been validated with:

- Raw artifact upload/download
- Docker image push/pull
- Python wheel/sdist upload
- Clean virtualenv install from Nexus PyPI
- Package execution after Nexus install

## Storage policy

Use local Friday disk for live Nexus data:

    /srv/devops/nexus/data

Use NFS for backups, archive exports, and StarkGrid-ingestable evidence:

    /mnt/starship/artifacts
    /mnt/starship/nexus-backups
    /mnt/starship/starkgrid-ingest/artifacts

Do not put active Nexus data directly on NFS unless the mount is proven stable and performant. Artifact managers and embedded databases behave better on local disk.
