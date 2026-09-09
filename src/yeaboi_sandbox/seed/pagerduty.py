"""Raise a real PagerDuty incident, and record what it became.

An incident is an event, not a resource, so Pulumi cannot declare it: the stack
builds the service and this raises one into it through Events API v2. What the
vendor assigns back — the incident number, the moment it was created — is the
seed ledger, and the fixture's ``ref`` and ``started_at`` expectations are
matched against exactly those values.

``urgency`` is the whole reason the expected severity is ``high``: PagerDuty
only has ``high`` and ``low``, and ``connectors/pagerduty.py`` feeds it straight
into ``clean_severity``. There is no way to make this connector emit
``critical``.
"""

from __future__ import annotations

from dataclasses import dataclass

from yeaboi_sandbox import envid

EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"
INCIDENTS_URL = "https://api.pagerduty.com/incidents"

#: PagerDuty's whole urgency vocabulary.
URGENCIES = ("high", "low")


@dataclass(frozen=True)
class Seeded:
    """What the vendor assigned, and what the fixture will assert against."""

    dedup_key: str
    ref: str
    title: str
    service: str
    created_at: str
    url: str


def dedup_key(slot: int, name: str) -> str:
    """Stable per environment and fixture, so a re-seed updates rather than piles up."""
    return f"{envid.env_id(slot)}-{name}"


def trigger_payload(slot: int, *, routing_key: str, service: str, name: str, urgency: str = "high") -> dict:
    """The Events API v2 body for one seeded incident.

    The title carries the environment id, which is what makes the assertion
    proof of isolation rather than just proof of arrival — an incident from
    another environment cannot satisfy a ``title_prefix`` for this one.
    """
    if urgency not in URGENCIES:
        raise ValueError(f"PagerDuty urgency is {URGENCIES}, got {urgency!r}")
    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": dedup_key(slot, name),
        "payload": {
            "summary": f"{envid.env_id(slot)} {name} latency exceeded",
            "source": service,
            "severity": "critical" if urgency == "high" else "info",
            "component": name,
        },
    }


def capture(rows: list[dict], *, dedup: str) -> Seeded | None:
    """Find the raised incident in a ``GET /incidents`` page and record it.

    Returns None while PagerDuty has not surfaced it yet — the caller polls to a
    deadline, and a miss inside that deadline is TIMEOUT rather than WRONG.
    """
    for row in rows:
        if str(row.get("incident_key") or "") != dedup:
            continue
        return Seeded(
            dedup_key=dedup,
            # connectors/pagerduty.py builds its ref from incident_number.
            ref=f"PD-{row.get('incident_number')}",
            title=str(row.get("title") or ""),
            service=str((row.get("service") or {}).get("summary") or ""),
            created_at=str(row.get("created_at") or ""),
            url=str(row.get("html_url") or ""),
        )
    return None
