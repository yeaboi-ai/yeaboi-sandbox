"""What every vendor component owes the harness.

Two obligations, and the second is a safety property rather than a convenience.

``env_vars`` is how a stack tells the runner which of yeaboi's env vars it
filled; ``envblock.build`` blanks everything else, so a vendor that forgets to
report one gets a blank rather than the developer's real credential.

``resource_names`` is every name this component creates inside a shared tenant.
``tests/unit/test_teardown_scope.py`` asserts each one renders through
``envid`` and carries the environment prefix — a literal name in a component is
a resource teardown cannot find and the sweeper will not match.
"""

from __future__ import annotations

from abc import abstractmethod

import pulumi

from yeaboi_sandbox import envid


class VendorComponent(pulumi.ComponentResource):
    """One vendor's slice of one environment."""

    #: The connector key. Must match a row in the tier registry.
    key: str = ""

    def __init__(self, slot: int, opts: pulumi.ResourceOptions | None = None):
        if not self.key:
            raise ValueError(f"{type(self).__name__} must set `key`")
        self.slot = envid.check(slot)
        self.env_id = envid.env_id(slot)
        super().__init__(f"yeaboi-sbx:vendor:{self.key}", self.env_id, None, opts)

    @property
    def child_opts(self) -> pulumi.ResourceOptions:
        return pulumi.ResourceOptions(parent=self)

    @property
    @abstractmethod
    def env_vars(self) -> pulumi.Output[dict]:
        """The env vars yeaboi reads for this connector, as this stack set them."""

    @property
    @abstractmethod
    def resource_names(self) -> tuple[str, ...]:
        """Every name created inside a shared tenant. All must carry the prefix."""

    def check_scope(self) -> None:
        """Refuse to build a component that names something outside its prefix."""
        stray = [n for n in self.resource_names if not envid.owned_by(n, self.slot)]
        if stray:
            raise ValueError(
                f"{self.key}: {stray} are outside this environment's prefix. "
                "Teardown deletes by prefix, so an unprefixed name is an orphan."
            )
