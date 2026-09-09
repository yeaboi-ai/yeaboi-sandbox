"""The operators, exercised against real OpsEvent shapes.

Actuals are built with yeaboi's own ``OpsEvent`` and ``asdict``, so a change to
the dataclass breaks these tests rather than letting the harness assert against
a shape yeaboi stopped producing.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

pytest.importorskip("yeaboi.ops.events", reason="the yeaboi wheel is not installed")

from yeaboi.ops.events import OpsEvent  # noqa: E402

from yeaboi_sandbox.assertlib.match import check_event, check_field  # noqa: E402
from yeaboi_sandbox.tiers.spec import ExpectedEvent, Match  # noqa: E402


def event(**over) -> dict:
    base = dict(
        kind="incident",
        source="pagerduty",
        ref="PD-4821",
        title="sbx-17 checkout latency exceeded",
        service="sbx-17-checkout",
        severity="high",
        status="triggered",
        started_at="2026-09-09T08:14:03Z",
        ended_at="",
        url="https://yeaboi-sbx.pagerduty.com/incidents/Q1ABC",
    )
    base.update(over)
    return asdict(OpsEvent(**base))


class TestEq:
    def test_exact(self):
        assert check_field("severity", Match(op="eq", value="high"), "high").ok

    def test_the_pagerduty_reality(self):
        # connectors/pagerduty.py feeds `urgency` into clean_severity, and
        # PagerDuty urgency is only high|low. A fixture that expected
        # "critical" would be asserting something the connector cannot emit.
        result = check_field("severity", Match(op="eq", value="critical"), "high")
        assert not result.ok


class TestIsoZWithin:
    RULE = Match(op="iso_z_within", value="2026-09-09T08:14:03Z", tolerance_s=90)

    def test_the_same_moment(self):
        assert check_field("started_at", self.RULE, "2026-09-09T08:14:03Z").ok

    def test_within_tolerance(self):
        assert check_field("started_at", self.RULE, "2026-09-09T08:15:00Z").ok

    def test_outside_tolerance_names_the_drift(self):
        result = check_field("started_at", self.RULE, "2026-09-09T09:14:03Z")
        assert not result.ok and "off by 3600s" in result.detail

    @pytest.mark.parametrize(
        "raw",
        [
            "2026-09-09T08:14:03+00:00",  # yeaboi's iso() rewrites this to Z
            "2026-09-09 08:14:03Z",
            "1789012443",  # Datadog's unix seconds, unconverted
            "",
        ],
    )
    def test_an_unnormalised_timestamp_fails_even_at_the_right_moment(self, raw):
        # The point of the operator: prove ops/events.py::iso() ran, not just
        # that the vendor knows what time it is.
        result = check_field("started_at", self.RULE, raw)
        assert not result.ok and "normalised" in result.detail


class TestUrlShape:
    RULE = Match(op="url_shape", host="yeaboi-sbx.pagerduty.com", path_glob="/incidents/*")

    def test_the_expected_shape(self):
        assert check_field("url", self.RULE, "https://yeaboi-sbx.pagerduty.com/incidents/Q1ABC").ok

    def test_a_tracking_parameter_is_tolerated(self):
        assert check_field("url", self.RULE, "https://yeaboi-sbx.pagerduty.com/incidents/Q1?utm_source=x").ok

    def test_http_is_refused(self):
        assert not check_field("url", self.RULE, "http://yeaboi-sbx.pagerduty.com/incidents/Q1").ok

    def test_the_wrong_host_is_refused(self):
        result = check_field("url", self.RULE, "https://evil.example/incidents/Q1")
        assert not result.ok and "host is evil.example" in result.detail

    @pytest.mark.parametrize("param", ["token", "api_key", "access_token", "code", "secret"])
    def test_a_credential_shaped_query_param_fails(self, param):
        # yeaboi renders these URLs onto screens and into exports.
        url = f"https://yeaboi-sbx.pagerduty.com/incidents/Q1?{param}=abc123"
        result = check_field("url", self.RULE, url)
        assert not result.ok and "carries" in result.detail


class TestCheckEvent:
    EXPECTED = ExpectedEvent(
        kind="incident",
        source="pagerduty",
        fields={
            "ref": Match(op="eq", value="PD-4821"),
            "service": Match(op="eq", value="sbx-17-checkout"),
            "severity": Match(op="eq", value="high"),
            "status": Match(op="eq", value="triggered"),
            "started_at": Match(op="iso_z_within", value="2026-09-09T08:14:03Z"),
        },
    )

    def test_a_seeded_incident_matches(self):
        assert check_event(self.EXPECTED, event()).ok

    def test_one_wrong_field_names_only_that_field(self):
        result = check_event(self.EXPECTED, event(severity="low"))
        assert not result.ok
        assert [f.field for f in result.failures] == ["severity"]

    def test_a_field_the_expectation_omits_is_not_checked(self):
        # `title` is not in EXPECTED, so a different title is not a failure.
        assert check_event(self.EXPECTED, event(title="something else entirely")).ok

    def test_the_wrong_kind_fails(self):
        assert not check_event(self.EXPECTED, event(kind="alert")).ok


def test_an_unknown_operator_is_refused():
    with pytest.raises(ValueError, match="unknown match operator"):
        check_field("severity", Match(op="nonsense", value="x"), "high")
