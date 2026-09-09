"""A row's env block must cover everything the connector actually needs.

Reads yeaboi's own descriptors rather than the vendored contract, because
``connectors.json`` at schema 3 carries no field information. This is the test
that catches a connector growing a new required credential.
"""

from __future__ import annotations

import pytest

from yeaboi_sandbox.tiers.registry import SANDBOX_ROWS

registry = pytest.importorskip("yeaboi.connectors.registry", reason="the yeaboi wheel is not installed")


def _connector(key: str):
    from yeaboi.connectors import legacy

    return registry.by_key(key) or legacy.by_key(key)


@pytest.mark.parametrize("row", SANDBOX_ROWS, ids=lambda r: r.key)
def test_row_declares_every_env_the_connector_reads(row):
    connector = _connector(row.key)
    assert connector is not None, f"{row.key} is not a connector yeaboi knows"
    declared = tuple(f.env for f in connector.fields)
    assert row.envs == declared, (
        f"{row.key}: env block drifted from the descriptor.\n"
        f"  descriptor: {declared}\n  row:        {row.envs}\n"
        "Regenerate rather than hand-editing — the descriptor is the source of truth."
    )
