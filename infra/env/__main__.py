"""One sandbox environment: every built Tier A connector, under one prefix.

The stack reads its slot from config and instantiates a component per built row
in the tier registry. Two exports: ``yeaboi_env`` (secret — the env vars the
runner hands yeaboi) and ``sbx`` (metadata, never secret).
"""

from __future__ import annotations

import pulumi

from infra.env.components.pagerduty import PagerDutyEnv
from yeaboi_sandbox import envid
from yeaboi_sandbox.tiers.registry import SANDBOX_ROWS

#: Which registry rows this stack can actually build yet. A row is added here in
#: the same change that adds its component, so `sbx tiers` and the stack agree.
BUILDERS = {"pagerduty": PagerDutyEnv}


def main() -> None:
    config = pulumi.Config()
    slot = envid.check(config.require_int("slot"))

    built = [r for r in SANDBOX_ROWS if r.key in BUILDERS]
    unbuilt = sorted({r.key for r in SANDBOX_ROWS if r.status == "built"} - set(BUILDERS))
    if unbuilt:
        raise ValueError(f"registry says these are built but the stack has no component: {unbuilt}")

    components = []
    if "pagerduty" in BUILDERS:
        pd_config = pulumi.Config("pagerduty")
        components.append(
            PagerDutyEnv(
                slot,
                bot_user_id=pd_config.require("botUserId"),
                api_key=pd_config.require_secret("apiKey"),
            )
        )

    pulumi.export(
        "yeaboi_env",
        pulumi.Output.secret(
            pulumi.Output.all(*[c.env_vars for c in components]).apply(
                lambda blocks: {k: v for block in blocks for k, v in block.items()}
            )
        ),
    )
    pulumi.export(
        "sbx",
        {
            "env_id": envid.env_id(slot),
            "slot": slot,
            "connectors": [c.key for c in components],
            "rows": len(built),
        },
    )
    keys = [c.key for c in components]
    pulumi.export(
        "seed_inputs",
        pulumi.Output.all(*[c.seed_inputs for c in components]).apply(
            lambda blocks: dict(zip(keys, blocks, strict=True))
        ),
    )


main()
