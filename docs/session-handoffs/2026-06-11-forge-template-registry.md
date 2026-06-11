# Forge Session Handoff — 2026-06-11

## Milestone

Forge reached an internal developer platform checkpoint.

Forge now supports:

- Python worker project scaffolding
- Optional Docker scaffold generation
- Optional Jenkinsfile generation
- Git init and remote setup
- Deterministic template artifact packaging
- SHA256 template manifests
- Template publishing to Nexus raw-hosted
- NFS archival of template artifacts and receipts
- StarkGrid ingest-ready evidence output

## Latest validated commit

8e9de84 Add Forge template Nexus publishing

Pushed to:

- Private Gitea: ssh://git@192.168.1.107:2222/portfolio/forge.git
- GitHub: git@github.com:qmcclellan/forge.git

## Validated Forge command

From:

    /srv/workspaces/projects/portfolio/forge

Command:

    source .venv/bin/activate
    python -m forge.cli template publish python-worker --version 0.1.0

This command successfully:

1. Packaged the python-worker template.
2. Created a deterministic tar.gz archive.
3. Created a SHA256 manifest.
4. Uploaded archive and manifest to Nexus raw-hosted.
5. Archived files to Veronica NFS.
6. Copied receipt and manifest into the StarkGrid ingest-ready lane.

## Published template

Template:

    python-worker

Version:

    0.1.0

Nexus raw-hosted location:

    http://192.168.1.107:8082/repository/raw-hosted/forge/templates/python-worker/0.1.0/

Files:

    python-worker-0.1.0.tar.gz
    python-worker-0.1.0.manifest.json

Validated deterministic archive SHA256:

    0bd4ee89eeedda27c2597d694904729f84a703f2307fc29a4465564996b4b665

The archive was downloaded back from Nexus and the SHA256 matched the manifest.

## NFS archive location

    /mnt/veronica-nfs/devops/nexus/artifacts/forge/templates/python-worker/0.1.0/

Contains:

    python-worker-0.1.0.tar.gz
    python-worker-0.1.0.manifest.json
    publish-receipt-20260611T014627Z.txt

## StarkGrid ingest-ready evidence

    /mnt/veronica-nfs/ingest/devops-artifacts/

Contains:

    forge-template-python-worker-0.1.0.manifest.json
    publish-receipt-20260611T014627Z.txt
    nexus-smoke-20260611T000613Z.txt

## Nexus / Friday artifact hub

Nexus runs on Friday.

Nexus UI:

    http://192.168.1.107:8082

Docker registry:

    192.168.1.107:5000

PyPI hosted:

    http://192.168.1.107:8082/repository/pypi-hosted/

Raw hosted:

    http://192.168.1.107:8082/repository/raw-hosted/

Validated Nexus capabilities:

- Raw artifact upload/download
- Docker image push/pull
- PyPI wheel/sdist upload
- Clean virtualenv install from Nexus PyPI
- Forge template raw-hosted publish/download
- SHA256 integrity check

## Friday / Veronica NFS layout

Friday mounts Veronica NFS at:

    /mnt/veronica-nfs

Live Nexus data remains local on Friday:

    /srv/devops/nexus/data

NFS archive and evidence paths:

    /mnt/veronica-nfs/devops/nexus/artifacts
    /mnt/veronica-nfs/devops/nexus/backups
    /mnt/veronica-nfs/devops/nexus/manifests
    /mnt/veronica-nfs/ingest/devops-artifacts

Important boundary:

    /mnt/veronica-nfs/artifacts/argus

That path is StarkGrid/Argus artifact space. Do not use it for Nexus or Forge DevOps dumps.

## Current platform model

Forge creates and publishes approved templates.
Gitea stores source code.
Jenkins builds, tests, and publishes project outputs.
Nexus stores packages, Docker images, raw artifacts, and Forge templates.
Veronica NFS stores archives, backups, and evidence.
StarkGrid indexes and searches evidence and manifests.
Coder and NoMachine provide portable developer access.

One-line summary:

    Forge creates the project, Gitea tracks it, Jenkins proves it, Nexus stores it, NFS archives it, and StarkGrid makes the evidence searchable.

## Next session plan

Do not start with Java, Spring, PyTorch, or other templates yet.

Next Forge feature:

    forge template pull

Goal:

- Download a Forge template from Nexus.
- Download its manifest.
- Verify SHA256.
- Extract it into a local template cache.
- Prepare for future Forge project creation from Nexus-backed template versions.

Possible future command:

    python -m forge.cli template pull python-worker --version 0.1.0

Later goal:

    forge new my-service --template python-worker --template-source nexus --template-version 0.1.0

## Hardware note

A 1 TB SSD is on its way for Friday.

Recommended future storage direction:

Friday 1 TB SSD:

- live Nexus data
- Docker layers
- Gitea active data
- Jenkins/Coder active caches

Veronica:

- SSD scratch later
- HDD/SAS HDD for cold archive, backups, and StarkGrid evidence

Mellanox / 10GbE becomes useful once SSD scratch and artifact movement are heavy enough that 1GbE becomes annoying.

## Follow-up update — Forge template pull validated

Forge now supports pulling a published template back from Nexus.

Validated command:

    python -m forge.cli template pull python-worker --version 0.1.0 --cache-dir /tmp/forge-template-pull-check

The command successfully:

1. Downloaded the template manifest from Nexus raw-hosted.
2. Downloaded the template archive from Nexus raw-hosted.
3. Verified the archive SHA256 against the manifest.
4. Extracted the template into the local template cache.

Validated SHA256:

    0bd4ee89eeedda27c2597d694904729f84a703f2307fc29a4465564996b4b665

Validated cache path:

    /tmp/forge-template-pull-check/python-worker/0.1.0/

Extracted template path:

    /tmp/forge-template-pull-check/python-worker/0.1.0/python-worker

Completed registry loop:

    package -> publish -> Nexus -> pull -> verify -> extract

Next recommended feature:

    forge new my-service --template python-worker --template-source nexus --template-version 0.1.0

Do not add new language templates until Forge can generate a project directly from a pulled Nexus-backed template.

## Follow-up update — Nexus-backed project creation validated

Forge now supports creating a new project directly from a verified Nexus-backed template.

Validated command:

    python -m forge.cli new nexus-worker \
      --template python-worker \
      --template-source nexus \
      --template-version 0.1.0 \
      --template-cache-dir /tmp/forge-template-new-cache \
      --output-dir /tmp/forge-nexus-new-check \
      --description "Generated from a verified Nexus-backed Forge template." \
      --with-docker \
      --with-jenkins

The command successfully:

1. Pulled the python-worker template from Nexus.
2. Verified the template archive SHA256 against the manifest.
3. Extracted the template into the local cache.
4. Generated a new project from the verified cached template.
5. Included Docker and Jenkins scaffold files.
6. Ran the generated project's smoke test successfully.

Validated generated project path:

    /tmp/forge-nexus-new-check/nexus-worker

Validated template cache path:

    /tmp/forge-template-new-cache/python-worker/0.1.0/python-worker

Completed approved-template launch flow:

    package -> publish -> Nexus -> pull -> verify -> extract -> generate project

Latest validated commit:

    a360ca9 Add Nexus-backed Forge project creation

Next recommended feature:

    Add a small registry/list command or improve template metadata before adding new language templates.

Recommended next command idea:

    python -m forge.cli template list --source nexus

Do not add Java/Spring/PyTorch templates until Forge can clearly show which approved templates and versions exist.

## Follow-up update — Nexus template listing validated

Forge now supports listing approved templates from Nexus.

Validated command:

    python -m forge.cli template list \
      --source nexus \
      --cache-dir /tmp/forge-template-new-cache

Validated output:

    TEMPLATE        VERSION    CACHED    ARCHIVE_SHA256
    python-worker   0.1.0      yes      0bd4ee89eeedda27c2597d694904729f84a703f2307fc29a4465564996b4b665

This gives Forge an internal template catalog.

Latest validated commit:

    7c7e120 Add Forge Nexus template listing

Current completed flow:

    template list -> package -> publish -> Nexus -> pull -> verify -> extract -> generate project

Next recommended feature:

    Add template metadata fields such as language, runtime, description, tags, and recommended use before adding Java/Spring/PyTorch templates.

## Follow-up update — Template metadata validated

Forge now supports template metadata through:

    templates/python-worker/template.json

Validated metadata fields:

    name
    language
    runtime
    description
    tags
    recommended_use

Validated metadata-backed template version:

    python-worker 0.1.1

Validated published archive SHA256:

    9a3f7d0515000855c2a8c1bf40e70338b368a725f5ab397b6b1f05ac3bd8f6f6

Validated behavior:

1. Metadata is included in the packaged manifest.
2. Metadata is published to Nexus through the manifest.
3. Forge template list displays language and runtime.
4. Forge pull verifies and caches the metadata-backed template.

Latest validated commit:

    4101cc1 Add Forge template metadata

Current Forge platform flow:

    template metadata -> package -> publish -> list -> pull -> verify -> extract -> generate project

Next recommended feature:

    Add a cleaner template detail command before adding more templates.

Possible command:

    python -m forge.cli template info python-worker --version 0.1.1 --source nexus

## Follow-up update — Template info command validated

Forge now supports detailed template inspection through:

    python -m forge.cli template info python-worker --version 0.1.1 --source nexus

Validated output includes:

    Template
    Version
    Language
    Runtime
    Cached
    Archive SHA256
    Description
    Tags
    Recommended use
    Manifest URL

Validated template:

    python-worker 0.1.1

Validated SHA256:

    9a3f7d0515000855c2a8c1bf40e70338b368a725f5ab397b6b1f05ac3bd8f6f6

Latest validated feature commit:

    14e7813 Add Forge Nexus template info

New runbook:

    docs/template-registry-runbook.md

Current complete Forge template platform flow:

    metadata -> package -> publish -> list -> info -> pull -> verify -> extract -> generate project

Next recommended step:

    Stop adding platform plumbing for the moment and do a short Q&A / positioning pass.

Possible Q&A topics:

    What is Forge?
    Why Nexus?
    Why not just copy templates from Git?
    What does this prove for DevOps?
    What should be added before Java/Spring/PyTorch templates?
