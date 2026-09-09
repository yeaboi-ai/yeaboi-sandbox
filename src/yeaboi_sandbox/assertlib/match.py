"""Compare a fetched ``OpsEvent`` against what the fixture said to expect.

The operator vocabulary exists because three fields cannot be known in advance
and the rest must not be loosened on their account. ``kind``, ``source``,
``severity``, ``status`` and ``service`` are *the mapping under test* and are
always exact; ``ref`` is a vendor-assigned id and is matched against a value
captured at seed time; ``started_at`` is a real clock; ``url`` carries whatever
tracking parameters the vendor feels like adding this quarter.

A field that is absent from the expectation is not checked. A field that is
present is checked exactly as written.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from yeaboi_sandbox.tiers.spec import ExpectedEvent, Match

#: A query parameter that must never appear in an event's URL, whatever the
#: vendor does. yeaboi renders these URLs onto screens and into exports.
FORBIDDEN_QUERY = frozenset({"token", "api_key", "apikey", "access_token", "code", "secret", "key"})

_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


@dataclass(frozen=True)
class FieldResult:
    field: str
    ok: bool
    expected: str
    actual: str
    detail: str = ""


def _parse_iso_z(text: str) -> datetime | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def check_field(name: str, rule: Match, actual: str) -> FieldResult:
    """One field against one rule."""
    actual = "" if actual is None else str(actual)

    if rule.op == "eq":
        return FieldResult(name, actual == rule.value, rule.value, actual)

    if rule.op == "matches":
        ok = bool(re.match(rule.value, actual))
        return FieldResult(name, ok, f"~ {rule.value}", actual, rule.reason)

    if rule.op == "iso_z_within":
        # Two claims in one: that yeaboi normalised the vendor's timestamp into
        # the Z form at all, and that it is the moment we seeded.
        if not _ISO_Z.match(actual):
            return FieldResult(
                name,
                False,
                f"ISO-8601 Z within {rule.tolerance_s}s",
                actual,
                "not normalised to the ...Z form yeaboi's iso() produces",
            )
        want, got = _parse_iso_z(rule.value), _parse_iso_z(actual)
        if want is None:
            return FieldResult(name, False, rule.value, actual, "the captured timestamp is unparseable")
        drift = abs(got - want)
        ok = drift <= timedelta(seconds=rule.tolerance_s)
        return FieldResult(
            name,
            ok,
            f"{rule.value} ±{rule.tolerance_s}s",
            actual,
            "" if ok else f"off by {int(drift.total_seconds())}s",
        )

    if rule.op == "url_shape":
        parsed = urlparse(actual)
        if parsed.scheme != "https":
            return FieldResult(name, False, f"https://{rule.host}{rule.path_glob}", actual, "not https")
        if rule.host and parsed.hostname != rule.host:
            return FieldResult(name, False, f"host {rule.host}", actual, f"host is {parsed.hostname}")
        if rule.path_glob and not fnmatch.fnmatch(parsed.path, rule.path_glob):
            return FieldResult(name, False, f"path {rule.path_glob}", actual, f"path is {parsed.path}")
        leaked = sorted(set(parse_qs(parsed.query)) & FORBIDDEN_QUERY)
        if leaked:
            return FieldResult(name, False, "no credential-shaped query params", actual, f"carries {leaked}")
        return FieldResult(name, True, f"https://{rule.host}{rule.path_glob}", actual)

    raise ValueError(f"unknown match operator {rule.op!r}")


@dataclass(frozen=True)
class EventResult:
    """One expected event against the actual it was paired with."""

    expected_ref: str
    fields: tuple[FieldResult, ...]
    actual: dict

    @property
    def ok(self) -> bool:
        return all(f.ok for f in self.fields)

    @property
    def failures(self) -> tuple[FieldResult, ...]:
        return tuple(f for f in self.fields if not f.ok)


def check_event(expected: ExpectedEvent, actual: dict) -> EventResult:
    fields = [
        FieldResult("kind", actual.get("kind") == expected.kind, expected.kind, str(actual.get("kind", ""))),
        FieldResult("source", actual.get("source") == expected.source, expected.source, str(actual.get("source", ""))),
    ]
    fields += [check_field(name, rule, actual.get(name, "")) for name, rule in expected.fields.items()]
    ref_rule = expected.fields.get("ref")
    return EventResult(expected_ref=ref_rule.value if ref_rule else "", fields=tuple(fields), actual=actual)
