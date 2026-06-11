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
