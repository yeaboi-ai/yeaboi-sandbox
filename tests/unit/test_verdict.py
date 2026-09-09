"""The verdicts, and the distinctions that keep the table readable."""

from __future__ import annotations

from dataclasses import asdict

import pytest

pytest.importorskip("yeaboi.ops.events", reason="the yeaboi wheel is not installed")

from yeaboi.ops.events import OpsEvent  # noqa: E402

from yeaboi_sandbox.assertlib.verdict import Verdict, foreign_events, judge  # noqa: E402
from yeaboi_sandbox.tiers.spec import Expect, ExpectedEvent, Match  # noqa: E402

SLOT = 17


def event(ref="PD-4821", slot=SLOT, **over) -> dict:
    base = dict(
        kind="incident",
        source="pagerduty",
        ref=ref,
        title=f"sbx-{slot} checkout latency exceeded",
        service=f"sbx-{slot}-checkout",
        severity="high",
        status="triggered",
        started_at="2026-09-09T08:14:03Z",
        url="https://yeaboi-sbx.pagerduty.com/incidents/Q1",
    )
    base.update(over)
    return asdict(OpsEvent(**base))


EXPECT = Expect(
    surface="fetch",
    target="pagerduty",
    events=(
        ExpectedEvent(
            kind="incident",
            source="pagerduty",
            fields={
                "ref": Match(op="eq", value="PD-4821"),
                "severity": Match(op="eq", value="high"),
                "service": Match(op="eq", value="sbx-17-checkout"),
            },
        ),
    ),
)


def test_the_seeded_incident_comes_back_correctly():
    assert judge(EXPECT, events=[event()], slot=SLOT).verdict is Verdict.OK


def test_a_connector_that_failed_is_not_a_wrong_answer():
    # gather() folds a vendor failure into a failed SourceResult rather than
    # raising, so "the vendor was down" must not read as "the mapping broke".
    out = judge(EXPECT, events=[], slot=SLOT, source_ok=False, source_error="rate limited")
    assert out.verdict is Verdict.SOURCE_FAILED and out.error == "rate limited"


class TestMissingIsNotTheSameAsWrong:
    def test_before_the_deadline_it_is_a_timeout(self):
        out = judge(EXPECT, events=[], slot=SLOT, deadline_reached=False)
        assert out.verdict is Verdict.TIMEOUT and out.missing == ("PD-4821",)

    def test_after_the_deadline_it_is_wrong(self):
        out = judge(EXPECT, events=[], slot=SLOT, deadline_reached=True)
        assert out.verdict is Verdict.WRONG and out.missing == ("PD-4821",)

    def test_a_returned_event_with_the_wrong_field_is_wrong_immediately(self):
        out = judge(EXPECT, events=[event(severity="low")], slot=SLOT)
        assert out.verdict is Verdict.WRONG
        assert [f.field for f in out.matched[0].failures] == ["severity"]


class TestContamination:
    def test_another_environments_event_in_our_window(self):
        out = judge(EXPECT, events=[event(), event(ref="PD-9", slot=42)], slot=SLOT)
        assert out.verdict is Verdict.CONTAMINATED
        assert out.foreign[0]["ref"] == "PD-9"

    def test_contamination_outranks_a_correct_match(self):
        # Every other result is suspect once the namespace is leaking, so this
        # is reported instead of OK rather than alongside it.
        out = judge(EXPECT, events=[event(), event(ref="PD-9", slot=42)], slot=SLOT)
        assert out.verdict is not Verdict.OK

    def test_an_unprefixed_event_is_not_foreign(self):
        # A vendor's own noise carries no sbx- prefix; it is not another
        # environment and must not be reported as contamination.
        stray = event(ref="PD-7", title="vendor maintenance", service="")
        assert foreign_events([stray], SLOT) == ()

    def test_the_prefix_trap(self):
        # sbx-1 must not see sbx-17 as its own, nor sbx-17 see sbx-1.
        assert foreign_events([event(slot=17)], 1)
        assert foreign_events([event(slot=1)], 17)


class TestClosedWorld:
    def test_an_unexpected_event_of_ours_is_extra(self):
        out = judge(EXPECT, events=[event(), event(ref="PD-5000")], slot=SLOT, closed_world=True)
        assert out.verdict is Verdict.EXTRA and out.extra == ("PD-5000",)

    def test_open_world_tolerates_it(self):
        out = judge(EXPECT, events=[event(), event(ref="PD-5000")], slot=SLOT, closed_world=False)
        assert out.verdict is Verdict.OK


def test_exact_count_is_enforced_when_stated():
    expect = Expect(surface="fetch", target="pagerduty", events=EXPECT.events, exact_count=2)
    out = judge(expect, events=[event()], slot=SLOT)
    assert out.verdict is Verdict.WRONG and "expected exactly 2" in out.notes[0]
