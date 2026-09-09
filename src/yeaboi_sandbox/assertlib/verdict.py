"""Turn a fetch result into a verdict, and keep the verdicts distinct.

A miss and a mismatch mean different things. A vendor that has not ingested the
seed yet is TIMEOUT and will pass on the next poll; a vendor that returned the
event with the wrong severity is WRONG and someone has to look. Conflating them
is how a harness becomes noise people stop reading, so they never share a name.

CONTAMINATED is the third: an event carrying another environment's prefix came
back inside our window. It means the namespace is not isolating, which is worse
than either of the others because every other result is now suspect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from yeaboi_sandbox import envid
from yeaboi_sandbox.assertlib.match import EventResult, check_event
from yeaboi_sandbox.tiers.spec import Expect


class Verdict(str, Enum):
    OK = "OK"
    WRONG = "WRONG"  # it came back and it is not what was seeded
    TIMEOUT = "TIMEOUT"  # it has not come back yet; poll again
    EXTRA = "EXTRA"  # closed-world only: something ours we did not expect
    CONTAMINATED = "CONTAMINATED"  # another environment's data is in our window
    SOURCE_FAILED = "SOURCE_FAILED"  # gather() reported the connector itself failed


#: The fields an event can carry an environment prefix in. `ref` is the vendor's
#: own id and never carries ours.
PREFIXED_FIELDS = ("title", "service")


@dataclass(frozen=True)
class Outcome:
    verdict: Verdict
    connector: str
    matched: tuple[EventResult, ...] = ()
    missing: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()
    foreign: tuple[dict, ...] = ()
    error: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.verdict is Verdict.OK


def foreign_events(events: list[dict], slot: int) -> tuple[dict, ...]:
    """Events carrying a *different* environment's prefix.

    Run on every fetch, closed-world or not: on a shared tenant this is the only
    thing that would notice two environments bleeding into each other.
    """
    found = []
    for event in events:
        for name in PREFIXED_FIELDS:
            other = envid.owned_slot(str(event.get(name, "") or ""))
            if other is not None and other != slot:
                found.append(event)
                break
    return tuple(found)


def _ours(events: list[dict], slot: int) -> list[dict]:
    """Events this environment seeded, by prefix on any prefixed field."""
    return [e for e in events if any(envid.owned_by(str(e.get(n, "") or ""), slot) for n in PREFIXED_FIELDS)]


def judge(
    expect: Expect,
    *,
    events: list[dict],
    slot: int,
    source_ok: bool = True,
    source_error: str = "",
    closed_world: bool = False,
    deadline_reached: bool = False,
) -> Outcome:
    """One fixture's expectation against what ``gather()` actually returned."""
    connector = expect.target

    if not source_ok:
        return Outcome(Verdict.SOURCE_FAILED, connector, error=source_error)

    foreign = foreign_events(events, slot)
    if foreign:
        return Outcome(Verdict.CONTAMINATED, connector, foreign=foreign)

    by_ref = {str(e.get("ref", "")): e for e in events}
    matched: list[EventResult] = []
    missing: list[str] = []
    for expected in expect.events:
        rule = expected.fields.get("ref")
        actual = by_ref.get(rule.value) if rule is not None and rule.op == "eq" else None
        if actual is None:
            missing.append(rule.value if rule is not None else f"<{expected.kind}>")
            continue
        matched.append(check_event(expected, actual))

    if missing:
        # Nothing came back for it. Before the deadline that is a vendor still
        # ingesting; after it, the seed is genuinely not there.
        return Outcome(
            Verdict.WRONG if deadline_reached else Verdict.TIMEOUT,
            connector,
            matched=tuple(matched),
            missing=tuple(missing),
        )

    if any(not m.ok for m in matched):
        return Outcome(Verdict.WRONG, connector, matched=tuple(matched))

    extra: tuple[str, ...] = ()
    if closed_world:
        expected_refs = {m.expected_ref for m in matched}
        extra = tuple(sorted({str(e.get("ref", "")) for e in _ours(events, slot)} - expected_refs))
        if extra:
            return Outcome(Verdict.EXTRA, connector, matched=tuple(matched), extra=extra)

    notes = ()
    if expect.exact_count is not None and len(matched) != expect.exact_count:
        return Outcome(
            Verdict.WRONG,
            connector,
            matched=tuple(matched),
            notes=(f"expected exactly {expect.exact_count} event(s), matched {len(matched)}",),
        )
    return Outcome(Verdict.OK, connector, matched=tuple(matched), extra=extra, notes=notes)
