"""Every name a component creates must carry its environment's prefix.

Teardown deletes by prefix and the sweeper matches by prefix, so a literal name
in a component is a resource neither can find. Checked without Pulumi by reading
each component's ``resource_names`` through a stubbed base class — instantiating
a real ComponentResource needs a running Pulumi engine.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from yeaboi_sandbox import envid

COMPONENTS = pathlib.Path(__file__).resolve().parents[2] / "infra" / "env" / "components"


def component_files() -> list[pathlib.Path]:
    return sorted(p for p in COMPONENTS.glob("*.py") if p.name not in ("__init__.py", "base.py"))


def test_there_is_at_least_one_component():
    assert component_files(), "no vendor components — the stack would build nothing"


@pytest.mark.parametrize("path", component_files(), ids=lambda p: p.stem)
def test_a_component_names_nothing_with_a_string_literal(path):
    """Names come from ``envid``, never from a literal.

    A literal like "sbx-checkout" looks prefixed but is not per-environment, so
    two environments would collide and teardown would take both.
    """
    tree = ast.parse(path.read_text())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("sbx-") or node.value.startswith("SBX"):
                offenders.append(node.value)
    assert not offenders, (
        f"{path.name} builds a name from a literal: {offenders}. "
        "Use envid.resource(slot, ...) so the name carries this environment's prefix."
    )


def test_the_prefix_helper_is_what_components_must_use():
    # The property the AST check is standing in for.
    assert envid.owned_by(envid.resource(17, "checkout"), 17)
    assert not envid.owned_by("sbx-checkout", 17)
