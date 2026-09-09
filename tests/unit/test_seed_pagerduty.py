"""The seed payload and the capture, without touching PagerDuty."""

from __future__ import annotations

import pytest

from yeaboi_sandbox.seed import pagerduty as seed


def test_the_title_carries_the_environment_id():
    # This is what makes the fetch assertion proof of isolation: an incident
    # from sbx-42 cannot satisfy sbx-17's expectation.
    payload = seed.trigger_payload(17, routing_key="R", service="sbx-17-checkout", name="checkout")
    assert payload["payload"]["summary"].startswith("sbx-17 ")
    assert payload["dedup_key"] == "sbx-17-checkout"


def test_the_dedup_key_makes_a_reseed_idempotent():
    assert seed.dedup_key(17, "checkout") == seed.dedup_key(17, "checkout")
    assert seed.dedup_key(17, "checkout") != seed.dedup_key(18, "checkout")


def test_pagerduty_has_only_two_urgencies():
    # A fixture asking for "critical" urgency would be asking for something the
    # vendor does not have, and the connector could never emit it either.
    with pytest.raises(ValueError, match="urgency"):
        seed.trigger_payload(17, routing_key="R", service="s", name="checkout", urgency="critical")


class TestCapture:
    ROW = {
        "incident_key": "sbx-17-checkout",
        "incident_number": 4821,
        "title": "sbx-17 checkout latency exceeded",
        "service": {"summary": "sbx-17-checkout"},
        "created_at": "2026-09-09T08:14:03Z",
        "html_url": "https://yeaboi-sbx.pagerduty.com/incidents/Q1ABC",
    }

    def test_the_ref_matches_what_the_connector_builds(self):
        # connectors/pagerduty.py derives its ref from incident_number.
        found = seed.capture([self.ROW], dedup="sbx-17-checkout")
        assert found is not None and found.ref == "PD-4821"

    def test_it_captures_what_the_fixture_asserts_on(self):
        found = seed.capture([self.ROW], dedup="sbx-17-checkout")
        assert found.created_at == "2026-09-09T08:14:03Z"
        assert found.service == "sbx-17-checkout"
        assert found.url.startswith("https://")

    def test_another_environments_incident_is_not_ours(self):
        other = dict(self.ROW, incident_key="sbx-42-checkout")
        assert seed.capture([other], dedup="sbx-17-checkout") is None

    def test_not_surfaced_yet_is_none_rather_than_an_error(self):
        # The caller polls to a deadline; a miss inside it is TIMEOUT.
        assert seed.capture([], dedup="sbx-17-checkout") is None
