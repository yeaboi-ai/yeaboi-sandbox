"""The one place an environment id becomes a vendor-legal name.

Every vendor spells a namespace differently and two of them impose hard limits
that bound the whole scheme: a Linear team key is at most 5 characters, and a
deleted Jira project key stays reserved for 60 days. So ids are never reused and
never wrap — a counter that reached the ceiling must alarm, not modulo.

Teardown correctness rests on :func:`owned_by`: a sweeper that deletes by
exclusion will eventually delete the shared environment, so matching is always a
positive test against this prefix.
"""

from __future__ import annotations

import re

#: The shared team environment. Never swept, never destroyed without an explicit
#: confirmation, because everything else keys off "is this env alive".
TEAM_SLOT = 1

#: Linear caps a team key at 5 characters ("S" + 4 digits), and that is what
#: bounds every environment id.
MAX_SLOT = 9999

#: Warn here so a ceiling is a planned migration rather than an outage.
WARN_SLOT = 9000

#: A sandbox-owned name. The negative lookahead is the whole point: without it
#: `sbx-1` matches `sbx-1234` and the sweeper eats the team environment.
OWNED_RE = re.compile(r"^sbx-(\d+)(?![0-9])")


class EnvIdError(ValueError):
    """A slot that cannot be turned into a legal vendor name."""


def check(slot: int) -> int:
    """Return ``slot`` if it can name an environment, else raise."""
    if not isinstance(slot, int) or isinstance(slot, bool):
        raise EnvIdError(f"slot must be an int, got {type(slot).__name__}")
    if slot < 1:
        raise EnvIdError(f"slot must be at least 1, got {slot}")
    if slot > MAX_SLOT:
        raise EnvIdError(
            f"slot {slot} exceeds the Linear team-key ceiling of {MAX_SLOT}. "
            "Ids are never reused — allocate a second sandbox workspace instead of wrapping."
        )
    return slot


def env_id(slot: int) -> str:
    """``sbx-17`` — the canonical id, and the Pulumi stack name."""
    return f"sbx-{check(slot)}"


def slug(slot: int) -> str:
    """``sbx-17`` — repos, Slack channels, DNS labels, Sentry projects."""
    return env_id(slot)


def upper(slot: int) -> str:
    """``SBX17`` — Jira project key and Confluence space key (alnum, alpha-first)."""
    return f"SBX{check(slot)}"


def short(slot: int) -> str:
    """``S17`` — a Linear team key, which may not exceed 5 characters."""
    return f"S{check(slot)}"


def tag(slot: int) -> str:
    """``env:sbx-17`` — Datadog, AWS and GCP labels."""
    return f"env:{env_id(slot)}"


def resource(slot: int, name: str) -> str:
    """``sbx-17-checkout`` — a prefixed resource inside a shared tenant."""
    return f"{slug(slot)}-{name}"


def owned_slot(name: str) -> int | None:
    """The slot a vendor resource name belongs to, or None if it is not ours.

    Used by the sweeper and by closed-world assertions, so it must never match a
    name the sandbox did not create.
    """
    found = OWNED_RE.match((name or "").strip())
    return int(found.group(1)) if found else None


def owned_by(name: str, slot: int) -> bool:
    """Whether ``name`` belongs to exactly this environment."""
    return owned_slot(name) == check(slot)
