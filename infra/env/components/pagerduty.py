"""PagerDuty: an escalation policy, a service, and somewhere to trigger into.

The incident itself is NOT a resource — it is raised through Events API v2 by
``seed/pagerduty.py``, because an incident is an event rather than a thing that
can be declared. Destroying the service is what reaps it.

The bot user is shared across every environment: PagerDuty's free plan caps at
five users, so a user per environment would exhaust it at five.
"""

from __future__ import annotations

import pulumi
import pulumi_pagerduty as pagerduty

from infra.env.components.base import VendorComponent
from yeaboi_sandbox import envid


class PagerDutyEnv(VendorComponent):
    key = "pagerduty"

    def __init__(self, slot: int, *, bot_user_id: str, api_key: pulumi.Input[str], opts=None):
        super().__init__(slot, opts)
        self._policy_name = envid.resource(slot, "oncall")
        self._service_name = envid.resource(slot, "checkout")
        self.check_scope()

        self.policy = pagerduty.EscalationPolicy(
            self._policy_name,
            name=self._policy_name,
            num_loops=1,
            rules=[
                pagerduty.EscalationPolicyRuleArgs(
                    escalation_delay_in_minutes=30,
                    targets=[pagerduty.EscalationPolicyRuleTargetArgs(type="user_reference", id=bot_user_id)],
                )
            ],
            opts=self.child_opts,
        )
        self.service = pagerduty.Service(
            self._service_name,
            name=self._service_name,
            escalation_policy=self.policy.id,
            # Never auto-resolve: a fixture that closed itself while the harness
            # was polling would read as a severity regression.
            auto_resolve_timeout="null",
            acknowledgement_timeout="null",
            opts=self.child_opts,
        )
        self.integration = pagerduty.ServiceIntegration(
            envid.resource(slot, "events"),
            name="events-v2",
            service=self.service.id,
            vendor=pagerduty.get_vendor(name="Events API V2").id,
            opts=self.child_opts,
        )
        self._api_key = api_key
        self.register_outputs({})

    @property
    def env_vars(self) -> pulumi.Output[dict]:
        return pulumi.Output.secret(pulumi.Output.from_input(self._api_key).apply(lambda k: {"PAGERDUTY_API_KEY": k}))

    @property
    def resource_names(self) -> tuple[str, ...]:
        return (self._policy_name, self._service_name, envid.resource(self.slot, "events"))

    @property
    def seed_inputs(self) -> pulumi.Output[dict]:
        """What the seeder needs: where to send the trigger, and what to call it."""
        return pulumi.Output.all(self.integration.integration_key, self.service.name).apply(
            lambda v: {"routing_key": v[0], "service": v[1]}
        )
