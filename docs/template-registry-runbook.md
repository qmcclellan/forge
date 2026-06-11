# Forge Template Registry Runbook

## Purpose

This runbook documents the Forge approved-template workflow.

Forge can now:

- package templates
- publish templates to Nexus
- list approved templates from Nexus
- show template metadata/details
- pull templates from Nexus
- verify template SHA256
- generate projects from verified Nexus-backed templates

## Current approved template

Template:

    python-worker

Metadata-backed version:

    0.1.1

Language:

    python

Runtime:

    python-3.12

Validated archive SHA256:

    9a3f7d0515000855c2a8c1bf40e70338b368a725f5ab397b6b1f05ac3bd8f6f6

## Template metadata file

Template metadata lives in:

    templates/python-worker/template.json

Validated fields:

    name
    language
    runtime
    description
    tags
    recommended_use

## Package template

Package a template locally:

    python -m forge.cli template package python-worker --version 0.1.1

This creates:

    dist/templates/python-worker-0.1.1.tar.gz
    dist/templates/python-worker-0.1.1.manifest.json

## Publish template to Nexus

Publish a template to Nexus raw-hosted:

    python -m forge.cli template publish python-worker --version 0.1.1

This uploads:

    python-worker-0.1.1.tar.gz
    python-worker-0.1.1.manifest.json

Nexus path:

    http://192.168.1.107:8082/repository/raw-hosted/forge/templates/python-worker/0.1.1/

## List approved templates

List templates from Nexus:

    python -m forge.cli template list --source nexus

Expected output shape:

    TEMPLATE        VERSION    CACHED    LANGUAGE    RUNTIME       ARCHIVE_SHA256
    python-worker   0.1.1      yes      python      python-3.12   9a3f7d0515000855c2a8c1bf40e70338b368a725f5ab397b6b1f05ac3bd8f6f6

## Show template details

Show full metadata for one template version:

    python -m forge.cli template info python-worker --version 0.1.1 --source nexus

Expected output includes:

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

## Pull template from Nexus

Pull and verify a template:

    python -m forge.cli template pull python-worker --version 0.1.1

This downloads the manifest and archive, verifies SHA256, and extracts the template into:

    ~/.forge/templates/python-worker/0.1.1/python-worker

## Generate project from Nexus-backed template

Create a project from the verified Nexus-backed template:

    python -m forge.cli new nexus-worker \
      --template python-worker \
      --template-source nexus \
      --template-version 0.1.1 \
      --description "Generated from a verified Nexus-backed Forge template." \
      --with-docker \
      --with-jenkins

Expected result:

    Forge pulls or reuses the cached approved template.
    Forge verifies the SHA256 through the manifest.
    Forge renders a working project.
    The generated project can run python -m pytest.

## Current approved-template flow

    metadata -> package -> publish -> list -> info -> pull -> verify -> extract -> generate project

## Rule before adding more templates

Do not add Java, Spring, PyTorch, or other templates until the template has:

- template.json metadata
- successful package test
- successful Nexus publish
- visible template list entry
- working template info output
- successful pull and SHA verification
- successful project generation
- passing generated project smoke test

## Approved Java Spring service template

Template:

    java-spring-service

Version:

    0.1.0

Language:

    java

Runtime:

    java-21

Validated archive SHA256:

    0dad24c3fa3a02daead19158cca1d4060df65a9dcb1e5c2399f67102842e804c

Validated approved-template flow:

    validate -> package -> publish -> list -> info -> pull -> generate -> verify

Validated commands:

    python -m forge.cli template validate java-spring-service
    python -m forge.cli template package java-spring-service --version 0.1.0
    python -m forge.cli template publish java-spring-service --version 0.1.0
    python -m forge.cli template list --source nexus
    python -m forge.cli template info java-spring-service --version 0.1.0 --source nexus
    python -m forge.cli template pull java-spring-service --version 0.1.0

Validated Nexus-backed project generation:

    python -m forge.cli new java-api \
      --template java-spring-service \
      --template-source nexus \
      --template-version 0.1.0 \
      --output-dir /tmp/forge-java-service-check \
      --description "Generated from a verified Nexus-backed Java Spring Forge template." \
      --with-docker \
      --with-jenkins

Validated generated files:

    pom.xml
    README.md
    template.json
    Dockerfile
    docker-compose.yml
    Jenkinsfile
    src/main/java/com/example/java_api/Application.java

Validated source check:

    grep -n "SpringApplication.run" /tmp/forge-java-service-check/java-api/src/main/java/com/example/java_api/Application.java
