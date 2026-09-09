"""The registry must name every connector yeaboi has, and no others.

Two-way set equality against the vendored catalog, the same shape
``tests/unit/test_surface_parity.py`` uses over in yeaboi: an addition upstream
and a deletion both go red, so the registry cannot silently fall behind.

Reads the vendored contract, not the installed wheel, so it runs on a bare CI
runner with nothing configured.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from yeaboi_sandbox.tiers.registry import SANDBOX_ROWS, keys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "contracts" / "v1" / "connectors.json"

_HOW_TO = (
    "Fix: add a SandboxConnector row in src/yeaboi_sandbox/tiers/registry.py. "
    "A new vendor starts at tier='C', status='pending' with a reason naming its tracking issue."
)


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG.read_text())


def test_contract_schema_is_the_one_we_parse(catalog):
    # The generator over in yeaboi could reshape this; fail loudly rather than
    # reading a key that quietly stopped existing.
    assert catalog["$schema_version"] == 3


def test_every_connector_has_a_row(catalog):
    upstream = {c["key"] for c in catalog["connectors"]}
    missing = upstream - keys()
    assert not missing, f"yeaboi has connectors with no sandbox row: {sorted(missing)}. {_HOW_TO}"


def test_no_row_for_a_connector_yeaboi_dropped(catalog):
    upstream = {c["key"] for c in catalog["connectors"]}
    extra = keys() - upstream
    assert not extra, f"sandbox rows for connectors yeaboi no longer has: {sorted(extra)}. {_HOW_TO}"


def test_every_b_and_c_row_states_a_reason():
    # Enforced in __post_init__ too; asserted here so the message names the rows.
    silent = [r.key for r in SANDBOX_ROWS if r.tier in ("B", "C") and not r.reason]
    assert not silent, f"tier B/C rows with no stated reason: {silent}"


def test_tier_c_rows_have_no_tenant():
    # Tier C means no tenant can exist. A tenant here would be a mis-tiering.
    wrong = [r.key for r in SANDBOX_ROWS if r.tier == "C" and (r.tenant or r.prefix_scope)]
    assert not wrong, f"tier C rows naming a tenant: {wrong}"


def test_build_progress_is_visible(capsys):
    # Not an assertion — the fan-out burn-down, printed on every run so the
    # remaining work is visible without being red.
    pending = sorted(r.key for r in SANDBOX_ROWS if r.status == "pending")
    built = sorted(r.key for r in SANDBOX_ROWS if r.status == "built")
    with capsys.disabled():
        print(f"\n  sandbox rows: {len(built)} built, {len(pending)} pending")
        if pending:
            print(f"  pending: {', '.join(pending)}")
