"""The prefix vocabulary, and the matching that teardown depends on."""

from __future__ import annotations

import pytest

from yeaboi_sandbox import envid


def test_the_vendor_forms():
    assert envid.env_id(17) == "sbx-17"
    assert envid.upper(17) == "SBX17"
    assert envid.short(17) == "S17"
    assert envid.tag(17) == "env:sbx-17"
    assert envid.resource(17, "checkout") == "sbx-17-checkout"


def test_linear_team_key_never_exceeds_five_characters():
    assert len(envid.short(envid.MAX_SLOT)) == 5


@pytest.mark.parametrize("bad", [0, -1, envid.MAX_SLOT + 1, True, "17", 1.0])
def test_illegal_slots_are_refused(bad):
    with pytest.raises(envid.EnvIdError):
        envid.check(bad)


@pytest.mark.parametrize(
    "name,slot",
    [
        ("sbx-1", 1),
        ("sbx-17", 17),
        ("sbx-17-checkout", 17),
        ("sbx-1234", 1234),
    ],
)
def test_owned_names_resolve_to_their_slot(name, slot):
    assert envid.owned_slot(name) == slot


@pytest.mark.parametrize("name", ["sbx-", "sbxy-1", "production-sbx-1", "", "SBX17", "sbx"])
def test_names_the_sandbox_does_not_own(name):
    assert envid.owned_slot(name) is None


def test_the_prefix_trap_that_would_eat_the_team_environment():
    # Without the negative lookahead, "sbx-1" matches "sbx-1234" and a sweeper
    # run for a dead environment would destroy the shared one.
    assert not envid.owned_by("sbx-1234", envid.TEAM_SLOT)
    assert envid.owned_by("sbx-1-checkout", envid.TEAM_SLOT)
