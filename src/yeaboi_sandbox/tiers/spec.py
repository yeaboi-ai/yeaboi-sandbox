"""What one sandbox row *is*, as data.

Mirrors the shape yeaboi's own ``connectors/spec.py`` uses: every fact a lane
needs about a connector lives on the descriptor, and the runner, the seeder and
the parity test all derive from here rather than restating it.

Stdlib only. ``tests/unit`` imports this on a runner with no credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

#: A = full IaC + seeded fixtures + exact-data assertions.
#: B = real tenant, one-time manual seed, verification only.
#: C = no tenant can exist; the recorded-cassette lane, with a stated reason.
Tier = Literal["A", "B", "C"]

#: Orthogonal to tier: the fan-out burn-down. Every connector has a row from day
#: one so the parity check is two-way; ``pending`` says the row is not built yet.
Status = Literal["built", "pending"]

#: How a field is compared. `eq` is exact and is what the mapping under test
#: deserves; the looser operators exist only for values a vendor assigns.
MatchOp = Literal["eq", "matches", "iso_z_within", "url_shape"]


@dataclass(frozen=True)
class Match:
    """One field's expectation on a fetched ``OpsEvent``."""

    op: MatchOp
    value: str = ""
    #: `iso_z_within` only: how far the vendor's clock may differ, in seconds.
    tolerance_s: int = 90
    #: `url_shape` only: the host the URL must be on, and a path glob.
    host: str = ""
    path_glob: str = ""
    #: Required when `op` is `matches` on `ref` — a captured id is always
    #: preferable, so loosening it has to be justified in the file.
    reason: str = ""


@dataclass(frozen=True)
class ExpectedEvent:
    """A partial ``OpsEvent``: every field named here must match exactly.

    ``title`` carries the environment id, which is what makes the assertion
    proof of isolation — an event seeded by another environment cannot satisfy
    it even when the tenant is shared.
    """

    kind: str
    source: str
    fields: dict[str, Match]


@dataclass(frozen=True)
class Expect:
    """One assertion against one yeaboi surface."""

    #: "verify" | "fetch" | "write" | "tool"
    surface: str
    #: The verify kind, the connector key, or a dotted "module:function".
    target: str
    events: tuple[ExpectedEvent, ...] = ()
    #: None means "at least len(events)". Set it where the environment owns an
    #: exclusive namespace and the result can be closed-world.
    exact_count: int | None = None
    #: How the window is chosen: "seeded" anchors to the stack's seed ledger,
    #: "now" uses a lookback from the current time, "pinned" reads a fixed
    #: window recorded at seed time.
    window: str = "seeded"
    #: Observation deadline. A miss inside it is TIMEOUT, never WRONG — the two
    #: verdicts mean different things and conflating them is how a harness
    #: becomes noise people stop reading.
    deadline_s: int = 60
    note: str = ""


@dataclass(frozen=True)
class SandboxConnector:
    """One connector's sandbox story, from tenant to assertion."""

    key: str
    tier: Tier
    status: Status
    #: "pulumi:<pkg>" | "bridge:<ns>/<name>" | "seeder" | "none"
    provisioner: str
    #: The hand-made tenant this row lives in; cross-referenced in docs/tenants.md.
    tenant: str
    #: What the environment id names inside that tenant.
    prefix_scope: str
    #: The exact env var names this row contributes to the block yeaboi reads.
    envs: tuple[str, ...]
    seeds: tuple[str, ...] = ()
    expects: tuple[Expect, ...] = ()
    #: Required on every B and C row.
    reason: str = ""
    #: For a B row: precisely what would promote it to A.
    promote_when: str = ""
    cost_note: str = ""

    def __post_init__(self) -> None:
        if self.tier in ("B", "C") and not self.reason:
            raise ValueError(f"{self.key}: tier {self.tier} needs a stated reason")
        if self.tier == "A" and self.status == "built" and not self.expects:
            raise ValueError(f"{self.key}: a built tier-A row needs at least one Expect")
        if self.tier == "C" and self.provisioner != "none":
            raise ValueError(f"{self.key}: tier C has no tenant, so it cannot have a provisioner")
