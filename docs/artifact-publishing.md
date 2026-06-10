# Artifact Publishing with Friday Nexus

Forge-generated projects can be built, tested, packaged, and published into the Friday Nexus artifact hub.

## Friday artifact hub

Nexus runs on Friday:

- Nexus UI: http://192.168.1.107:8082
- Docker registry: 192.168.1.107:5000
- PyPI hosted: http://192.168.1.107:8082/repository/pypi-hosted/
- Raw hosted: http://192.168.1.107:8082/repository/raw-hosted/

## Validated repositories

- raw-hosted: Raw evidence files, logs, release bundles, and reports.
- pypi-hosted: Python wheels and source distributions.
- docker-hosted: Docker/OCI images.

## Build and publish a Python package

From a Forge-generated Python project:

```bash
cd /srv/workspaces/projects/portfolio/<project-name>
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pytest

python -m pip install build twine
python -m build
