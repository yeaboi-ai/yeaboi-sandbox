"""The isolation guarantees, asserted rather than promised."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("yeaboi.connectors.registry", reason="the yeaboi wheel is not installed")

from yeaboi_sandbox import envblock  # noqa: E402


@pytest.fixture
def home(tmp_path):
    return tmp_path / "sbx" / "sbx-17"


def test_every_declared_env_is_set_even_when_the_sandbox_has_no_value(home):
    block = envblock.build({"PAGERDUTY_API_KEY": "seeded"}, yeaboi_home=home)
    declared = envblock.declared_envs()
    assert set(declared) <= set(block.env), "a declared env was left unset"
    assert block.env["PAGERDUTY_API_KEY"] == "seeded"


def test_a_production_token_in_the_parent_cannot_leak_through(home):
    # The exact hazard: GITHUB_TOKEN exported in the developer's shell, and a
    # stack that provisioned no GitHub environment.
    parent = {"PATH": os.environ["PATH"], "GITHUB_TOKEN": "ghp_realproductiontoken"}
    block = envblock.build({"PAGERDUTY_API_KEY": "seeded"}, yeaboi_home=home, parent=parent)
    assert block.env["GITHUB_TOKEN"] == ""
    assert "GITHUB_TOKEN" in block.blanked


def test_an_unrecognised_env_is_refused(home):
    with pytest.raises(envblock.IsolationError, match="no connector declares"):
        envblock.build({"PAGERDUTY_APIKEY": "typo"}, yeaboi_home=home)


def test_yeaboi_home_may_never_be_the_real_one():
    with pytest.raises(envblock.IsolationError, match="real ~/.yeaboi"):
        envblock.build({}, yeaboi_home=Path(os.path.expanduser("~")) / ".yeaboi")


def test_home_is_moved_so_the_real_env_file_is_not_on_disk(home):
    block = envblock.build({}, yeaboi_home=home, isolate_home=True)
    assert Path(block.env["HOME"]) != Path(os.path.expanduser("~"))
    assert str(home) in block.env["HOME"]


def test_exports_quote_hostile_values(home):
    block = envblock.build({"PAGERDUTY_API_KEY": "it's a 'token'"}, yeaboi_home=home)
    line = [row for row in block.exports().splitlines() if row.startswith("export PAGERDUTY_API_KEY=")][0]
    assert line == """export PAGERDUTY_API_KEY='it'\\''s a '\\''token'\\'''"""


def test_the_real_config_file_fingerprint_is_stable(tmp_path):
    target = tmp_path / ".env"
    assert envblock.fingerprint(target) == ""
    target.write_text("JIRA_API_TOKEN=x")
    first = envblock.fingerprint(target)
    assert first and envblock.fingerprint(target) == first
