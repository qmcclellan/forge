"""Read-only availability preflight for a proposed Forge project.

Checks whether a project name can safely be created -- locally and as a
Gitea repository -- before any scaffold, directory, or repository actually
exists. This module creates nothing: no directory, no file, no Git
repository, no network write of any kind. It only answers the question
"would `forge new` collide with something that already exists?".

Decision contract
------------------
Exactly one of four decisions is always returned:

* ``AVAILABLE``     -- the name is free, both locally and on Gitea.
* ``COLLISION``      -- the name already exists, locally or on Gitea (or
  both); ``collision_details`` says which.
* ``INVALID_NAME``   -- the name does not produce a usable Forge slug, so
  availability was never checked at either layer.
* ``UNKNOWN``        -- the Gitea query could not be answered (auth
  failure, network timeout, service unavailable, or no credential
  configured). This is never collapsed into ``AVAILABLE``: a query that
  failed to answer is not the same as a query that answered "no".

Credential model
-----------------
This module holds no Gitea credential itself and does not search the host
for one. ``default_gitea_probe`` reads a single, explicitly-named
environment variable (``GITEA_PROJECT_FACTORY_TOKEN``); if it is unset,
the probe fails closed (``reachable=False``) rather than guessing or
falling back to a different credential. A caller that already has its own
authorized Gitea interface (for example, an MCP connector already attached
to the orchestrating session) should pass it in as ``gitea_probe`` instead
of relying on the environment-variable default.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

DECISIONS = ("AVAILABLE", "COLLISION", "INVALID_NAME", "UNKNOWN")

_GITEA_TOKEN_ENV_VAR = "GITEA_PROJECT_FACTORY_TOKEN"
_GITEA_BASE_URL_ENV_VAR = "GITEA_API_BASE_URL"
_DEFAULT_GITEA_BASE_URL = "http://127.0.0.1:3000"


@dataclass(frozen=True)
class GiteaProbeResult:
    """The outcome of one read-only Gitea repository-existence query.

    ``exists`` is ``None`` whenever ``reachable`` is ``False`` -- a failed
    query has no opinion on existence, it is simply unanswered.
    """

    reachable: bool
    exists: bool | None
    detail: str


class GiteaProbe(Protocol):
    """Callable contract for a read-only Gitea repository-existence check."""

    def __call__(self, owner: str, repo_slug: str) -> GiteaProbeResult: ...


def default_gitea_probe(owner: str, repo_slug: str, *, timeout: float = 5.0) -> GiteaProbeResult:
    """Real, read-only ``GET /api/v1/repos/{owner}/{repo}`` existence check.

    Reads its credential from ``GITEA_PROJECT_FACTORY_TOKEN`` only. Never
    searches for a token anywhere else, never embeds one, and never falls
    back to a different one. Every failure mode (missing credential,
    network error, timeout, non-2xx/404 status) returns
    ``reachable=False`` -- this function never raises for an ordinary
    network or auth failure, so a caller cannot accidentally treat an
    exception's absence as a successful "available" answer.
    """
    token = os.environ.get(_GITEA_TOKEN_ENV_VAR)
    if not token:
        return GiteaProbeResult(
            reachable=False,
            exists=None,
            detail=f"{_GITEA_TOKEN_ENV_VAR} is not set; no Gitea credential configured",
        )

    base_url = os.environ.get(_GITEA_BASE_URL_ENV_VAR, _DEFAULT_GITEA_BASE_URL)
    url = f"{base_url.rstrip('/')}/api/v1/repos/{owner}/{repo_slug}"
    request = urllib.request.Request(url, headers={"Authorization": f"token {token}"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status == 200:
                return GiteaProbeResult(reachable=True, exists=True, detail="repository exists")
            return GiteaProbeResult(
                reachable=False,
                exists=None,
                detail=f"unexpected Gitea response status: {response.status}",
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return GiteaProbeResult(reachable=True, exists=False, detail="no repository with this name")
        if exc.code in (401, 403):
            return GiteaProbeResult(
                reachable=False,
                exists=None,
                detail=f"Gitea authentication failed (HTTP {exc.code})",
            )
        return GiteaProbeResult(
            reachable=False,
            exists=None,
            detail=f"unexpected Gitea response status: {exc.code}",
        )
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return GiteaProbeResult(reachable=False, exists=None, detail=f"Gitea unreachable: {exc}")


def check_project_availability(
    name: str,
    target_workspace: str | Path,
    gitea_owner: str,
    template: str | None = None,
    *,
    gitea_probe: GiteaProbe = default_gitea_probe,
) -> dict[str, Any]:
    """Check whether ``name`` could be created without colliding.

    Creates nothing. Performs exactly one local filesystem read
    (``Path.exists()``) and, unless the name is already invalid, exactly
    one Gitea query through ``gitea_probe``.

    Parameters
    ----------
    name:
        The proposed project's human-readable name, exactly as a caller
        would pass it to ``forge new``.
    target_workspace:
        The directory under which the project's slug-named folder would be
        created (mirrors ``forge new``'s own ``--output-dir`` /
        ``create_project`` target computation exactly, so this function's
        answer matches what ``forge new`` would actually do).
    gitea_owner:
        The Gitea user or organization namespace the repository would be
        created under.
    template:
        Optional; recorded in the result for provenance only. Does not
        change the decision logic.
    gitea_probe:
        Injectable Gitea existence check. Defaults to
        ``default_gitea_probe``. Tests should pass a fake/mock here rather
        than monkeypatching network internals.

    Returns
    -------
    A dict with stable keys: ``project_name``, ``project_slug``,
    ``template``, ``decision``, ``local_availability``,
    ``gitea_availability``, ``provider_reachable``, ``collision_details``,
    ``validation_errors``.
    """
    # Imported lazily, not at module scope: `forge.cli` imports this module
    # (to expose the `project check-availability` subcommand), so a
    # top-level import here would be a circular import. `slugify` and
    # `SLUG_PATTERN` are the single, existing source of truth for what a
    # valid Forge slug is -- deliberately reused rather than redefined, so
    # this preflight can never silently drift from what `forge new` itself
    # would actually accept (the exact class of bug KS-0017 fixed).
    from forge.cli import SLUG_PATTERN, slugify

    validation_errors: list[str] = []
    slug = slugify(name)

    if not slug or not SLUG_PATTERN.fullmatch(slug):
        validation_errors.append(
            f"project name does not produce a usable Forge slug: {name!r} -> {slug!r}"
        )
        return {
            "project_name": name,
            "project_slug": slug,
            "template": template,
            "decision": "INVALID_NAME",
            "local_availability": None,
            "gitea_availability": None,
            "provider_reachable": None,
            "collision_details": [],
            "validation_errors": validation_errors,
        }

    local_path = Path(target_workspace).expanduser().resolve() / slug
    local_exists = local_path.exists()
    local_availability = {"path": str(local_path), "exists": local_exists}

    probe_result = gitea_probe(gitea_owner, slug)
    gitea_availability = {
        "owner": gitea_owner,
        "repository": slug,
        "exists": probe_result.exists,
        "detail": probe_result.detail,
    }

    collision_details: list[str] = []
    if local_exists:
        collision_details.append(f"local path already exists: {local_path}")
    if probe_result.exists is True:
        collision_details.append(f"Gitea repository already exists: {gitea_owner}/{slug}")

    if collision_details:
        decision = "COLLISION"
    elif not probe_result.reachable:
        decision = "UNKNOWN"
    else:
        decision = "AVAILABLE"

    return {
        "project_name": name,
        "project_slug": slug,
        "template": template,
        "decision": decision,
        "local_availability": local_availability,
        "gitea_availability": gitea_availability,
        "provider_reachable": probe_result.reachable,
        "collision_details": collision_details,
        "validation_errors": validation_errors,
    }


def check_project_availability_json(
    name: str,
    target_workspace: str | Path,
    gitea_owner: str,
    template: str | None = None,
    *,
    gitea_probe: GiteaProbe = default_gitea_probe,
) -> str:
    result = check_project_availability(
        name, target_workspace, gitea_owner, template, gitea_probe=gitea_probe
    )
    return json.dumps(result, indent=2, sort_keys=True)
