# Forge Approved Template Platform Status — 2026-06-11

## Current status

Forge is now an approved-template platform backed by Nexus.

Validated flow:

    metadata -> validate -> package -> publish -> list -> info -> pull -> verify -> extract -> generate project

## Approved templates

    python-worker 0.1.1
    java-spring-service 0.1.0

## Current Nexus role

Nexus is the private artifact hub for Forge.

It currently supports:

- Forge template artifacts through raw-hosted
- Python package publishing through PyPI hosted
- Docker image publishing through Docker registry
- NFS archival receipts and manifests
- StarkGrid ingest-ready evidence

## Next Nexus expansion

Use the existing Maven repositories:

- maven-central proxy
- maven-releases hosted
- maven-snapshots hosted
- maven-public group

Goal:

    Java projects should resolve dependencies through Nexus.
    Jenkins should publish Java build artifacts to Nexus.
    Future Java templates should use Nexus as the default internal dependency source.

## Private CDN framing

Nexus is not a public edge CDN.

For this platform, Nexus acts as a private artifact registry, dependency cache, and internal distribution hub.

Better portfolio phrase:

    Private artifact registry and dependency cache for an internal developer platform.

## Current proof

Forge can:

- validate templates
- package templates
- publish templates to Nexus
- list approved templates
- show template metadata
- pull templates from Nexus
- verify SHA256
- generate projects from verified Nexus-backed templates

## Recommended next work

Do not add PyTorch yet.

Next best platform work:

1. Use the existing Maven proxy/hosted/group repositories in Nexus.
2. Configure Java template Maven settings for Nexus.
3. Let Jenkins build Java projects and publish JARs to Nexus.
4. Add node-dashboard later through the same approved-template gate.


## Maven repository note

Nexus already has the standard Maven repositories available:

    maven-central
    maven-public
    maven-releases
    maven-snapshots

Use maven-public as the main Maven URL for generated Java projects and Jenkins builds.

The duplicate repositories:

    maven-releases2
    maven-snapshots2

were removed after confirming the standard Maven repositories already existed.

## Java Spring service 0.1.1 approval

The Java Spring service template was upgraded from 0.1.0 to 0.1.1.

Approved template:

    java-spring-service 0.1.1

Validated archive SHA256:

    1214e2fdf5c01c0c006221a50108938ca3dffd7b1d2b40b5e2c7690a0e0d31ad

Validated feature:

    Generated Java projects include Maven Nexus settings.

Generated files:

    .mvn/maven.config
    .mvn/settings.xml

Maven endpoint:

    http://192.168.1.107:8082/repository/maven-public/

Validated real generated project:

    /srv/workspaces/projects/portfolio/generated-projects/backend/java/java-nexus-api-011

Validated flow:

    validate -> publish -> list -> info -> pull -> verify SHA256 -> generate from Nexus -> verify Maven Nexus settings

Latest Java template commit:

    b6f9adb Add Nexus Maven settings to Java template

## Node dashboard 0.1.0 approval

Approved template:

    node-dashboard 0.1.0

Runtime:

    node-20

Validated archive SHA256:

    05493e35fa1e30c80192dbc29b122753d96f0d4fa699c3f89ba77e55bf8caca3

Validated feature:

    Generated frontend dashboard projects include Vite-style React layout, Docker support, and Jenkins pipeline support.

Validated real generated project:

    /srv/workspaces/projects/portfolio/generated-projects/frontend/node/forge-dashboard-010

Validated flow:

    validate -> publish -> list -> info -> pull -> verify SHA256 -> generate from Nexus -> verify frontend files

Latest Node template commits:

    56f2d09 Add Node dashboard Forge template
    6a517a8 Fix Node dashboard template validation

Current approved template catalog:

    python-worker 0.1.1
    java-spring-service 0.1.1
    node-dashboard 0.1.0

## Default output lanes

Forge now supports default output lanes for generated projects.

If --output-dir is not provided, Forge places projects by template type:

    python-worker        -> /srv/workspaces/projects/portfolio/generated-projects/backend/python
    java-spring-service  -> /srv/workspaces/projects/portfolio/generated-projects/backend/java
    node-dashboard       -> /srv/workspaces/projects/portfolio/generated-projects/frontend/node

Validated generated projects:

    /srv/workspaces/projects/portfolio/generated-projects/backend/python/auto-python-worker
    /srv/workspaces/projects/portfolio/generated-projects/backend/java/auto-java-api
    /srv/workspaces/projects/portfolio/generated-projects/frontend/node/auto-node-dashboard
    /srv/workspaces/projects/portfolio/generated-projects/backend/java/customer-api

Manual override remains available through:

    --output-dir

Latest lane commit:

    d8a2ad1 Add default output lanes for Forge projects

## Node dashboard 0.1.1 npm Nexus approval

The Node dashboard template was upgraded from 0.1.0 to 0.1.1.

Approved template:

    node-dashboard 0.1.1

Validated feature:

    Generated Node projects include .npmrc pointing to Nexus npm-public.

npm endpoint:

    http://192.168.1.107:8082/repository/npm-public/

Generated file:

    .npmrc

Validated real generated project:

    /srv/workspaces/projects/portfolio/generated-projects/frontend/node/forge-dashboard-011

Current package manager status:

    Java projects resolve Maven dependencies through Nexus maven-public.
    Node projects resolve npm dependencies through Nexus npm-public.

Recommended stopping point:

    Stop Forge platform work here and begin scaffolding portfolio projects.
