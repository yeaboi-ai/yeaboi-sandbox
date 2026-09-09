"""Every yeaboi connector, and how the sandbox proves it.

One row per connector, always — a connector with no sandbox story still gets a
row saying so, because ``tests/unit/test_tier_parity.py`` compares this set
against the vendored catalog in both directions. That is what stops the repo
rotting when yeaboi adds a vendor.

``envs`` is generated from yeaboi's own descriptors and held to them by
``test_env_parity.py``; it is never hand-edited. ``status`` is the fan-out
burn-down and is orthogonal to ``tier``.
"""

from __future__ import annotations

from yeaboi_sandbox.tiers.spec import SandboxConnector

#: Ordered by tier then key, so a diff that promotes a row is easy to read.
SANDBOX_ROWS: tuple[SandboxConnector, ...] = (
    SandboxConnector(
        key="aws",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-aws",
        tenant="aws-sandbox-account",
        prefix_scope="alarm names: sbx-<n>-*",
        envs=(
            "AWS_AUTH_METHOD",
            "AWS_ROLE_ARN",
            "AWS_EXTERNAL_ID",
            "AWS_CLOUD_REGION",
        ),
        seeds=(
            "CloudWatch alarm sbx-<n>-checkout",
            "set-alarm-state to force it into ALARM — the most controllable fixture in the set",
        ),
        cost_note=(
            "must be a SEPARATE account: the fetcher reads DescribeAlarmHistory account-wide, so seeding in the "
            "production account pollutes real alarm history and may page a human."
        ),
    ),
    SandboxConnector(
        key="azdevops",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-azuredevops",
        tenant="azdevops-sandbox-org",
        prefix_scope="project names: sbx-<n>",
        envs=(
            "AZURE_DEVOPS_ORG_URL",
            "AZURE_DEVOPS_TOKEN",
        ),
        seeds=(
            "project sbx-<n>",
            "a repo",
            "two iterations",
            "work items across states",
        ),
        cost_note=(
            "_verify_azdevops exists but is NOT in LEGACY_VERIFY_KINDS, so verify_connection cannot reach it; this row "
            "asserts the function directly and pins the gap."
        ),
    ),
    SandboxConnector(
        key="bitbucket",
        tier="A",
        status="pending",
        provisioner="bridge:DrFaust92/bitbucket",
        tenant="bitbucket-sandbox-workspace",
        prefix_scope="repository slugs: sbx-<n>-*",
        envs=(
            "BITBUCKET_EMAIL",
            "BITBUCKET_API_TOKEN",
            "BITBUCKET_WORKSPACE",
        ),
        seeds=(
            "repo sbx-<n>-api",
            "one pipeline run",
        ),
        cost_note="free tier is 5 users and 50 Pipelines minutes/month.",
    ),
    SandboxConnector(
        key="circleci",
        tier="A",
        status="pending",
        provisioner="bridge:mrolla/circleci",
        tenant="circleci-org-yeaboi-sandbox",
        prefix_scope="follows the sandbox GitHub org's sbx-<n>-* repos",
        envs=(
            "CIRCLECI_TOKEN",
            "CIRCLECI_ORG_SLUG",
        ),
        seeds=(
            "follow sbx-<n>-api",
            "trigger one pipeline through API v2",
        ),
        cost_note="CIRCLECI_ORG_SLUG names a VCS org, which is why the GitHub sandbox must be its own org.",
    ),
    SandboxConnector(
        key="confluence",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="atlassian-site-yeaboi-sbx",
        prefix_scope="space key: SBX<n>",
        envs=(
            "CONFLUENCE_BASE_URL",
            "CONFLUENCE_EMAIL",
            "CONFLUENCE_API_TOKEN",
            "CONFLUENCE_SPACE_KEY",
        ),
        seeds=(
            "space SBX<n>",
            "three pages, one nested",
        ),
        cost_note="shares the Atlassian site and identity with jira; its fields fall back to the JIRA_ ones.",
    ),
    SandboxConnector(
        key="github",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-github",
        tenant="github-org-yeaboi-sandbox",
        prefix_scope="repository names inside the yeaboi-sandbox org: sbx-<n>-*",
        envs=("GITHUB_TOKEN",),
        seeds=(
            "repo sbx-<n>-api with a README and 3 labels",
            "6 issues, 2 of them closed",
            "one open PR from feature/seed",
        ),
        cost_note="free; a GitHub App installed only on the sandbox org mints a 1-hour token per run.",
    ),
    SandboxConnector(
        key="gitlab",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-gitlab",
        tenant="gitlab-sandbox-group",
        prefix_scope="project paths under the sandbox group: sbx-<n>-*",
        envs=(
            "GITLAB_TOKEN",
            "GITLAB_BASE_URL",
        ),
        seeds=(
            "group sbx-<n>",
            "two projects, each with a 5-second .gitlab-ci.yml",
            "one pipeline run per project",
        ),
        cost_note="400 free CI minutes/month; the fetcher is N+1 across projects, so keep it at two.",
    ),
    SandboxConnector(
        key="grafana",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-grafana",
        tenant="grafana-cloud-free-stack",
        prefix_scope="folder and rule names: sbx-<n>-*",
        envs=(
            "GRAFANA_BASE_URL",
            "GRAFANA_API_TOKEN",
        ),
        seeds=(
            "folder sbx-<n>",
            "one ALWAYS-FIRING alert rule on the TestData datasource, with a severity label",
        ),
        cost_note="Grafana Cloud free gives a public HTTPS host, so no self-hosting is needed.",
    ),
    SandboxConnector(
        key="jenkins",
        tier="A",
        status="pending",
        provisioner="bridge:taiidani/jenkins",
        tenant="jenkins-self-hosted-on-aws",
        prefix_scope="a folder per environment: sbx-<n>/",
        envs=(
            "JENKINS_BASE_URL",
            "JENKINS_USER",
            "JENKINS_API_TOKEN",
        ),
        seeds=(
            "folder sbx-<n>",
            "one freestyle job",
            "two builds, one failing",
        ),
        cost_note=(
            "the only vendor with no vendor: Fargate + ALB + ACM, ~$15-30/month. assert_safe_url demands public HTTPS, "
            "so it needs a real cert. Shared env only, never per-PR."
        ),
    ),
    SandboxConnector(
        key="jira",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="atlassian-site-yeaboi-sbx",
        prefix_scope="project key: SBX<n>",
        envs=(
            "JIRA_BASE_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
        ),
        seeds=(
            "project SBX<n> with a scrum board",
            "one sprint",
            "epics, stories and sub-tasks",
            (
                "SBXHARD: one deliberately hostile project with a required custom field, non-default issue type names "
                "and an extra workflow transition"
            ),
        ),
        cost_note=(
            "a deleted Jira project key stays RESERVED FOR 60 DAYS, which is why ids are never reused; teardown must "
            "also purge from trash."
        ),
    ),
    SandboxConnector(
        key="launchdarkly",
        tier="A",
        status="pending",
        provisioner="bridge:launchdarkly/launchdarkly",
        tenant="launchdarkly-sandbox-account",
        prefix_scope="project keys: sbx-<n>",
        envs=("LAUNCHDARKLY_API_KEY",),
        seeds=(
            "project sbx-<n>",
            "two flags",
            "a flag toggle, which is what writes the audit log",
        ),
        cost_note="the fetcher reads the audit log, so the seed is a change, not a resource.",
    ),
    SandboxConnector(
        key="linear",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="linear-sandbox-workspace",
        prefix_scope="team key: S<n> — capped at 5 chars, which bounds every id",
        envs=(
            "LINEAR_API_KEY",
            "LINEAR_TEAM_KEY",
        ),
        seeds=(
            "team S<n>",
            "one cycle",
            "four issues, two labels",
        ),
        cost_note=(
            "free tier caps at 250 issues and sync CREATES issues, so the reaper must archive sandbox "
            "issues older than 7 days."
        ),
    ),
    SandboxConnector(
        key="notion",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="notion-sandbox-workspace",
        prefix_scope="a root page per environment: sbx-<n>",
        envs=("NOTION_TOKEN",),
        seeds=(
            "root page sbx-<n>",
            "a database",
            "three child pages",
        ),
        cost_note="free, but rate-limited to ~3 requests/second — the tightest limit in the set.",
    ),
    SandboxConnector(
        key="pagerduty",
        tier="A",
        status="pending",
        provisioner="pulumi:pulumi-pagerduty",
        tenant="pd-sandbox-account",
        prefix_scope="service and escalation-policy names: sbx-<n>-*",
        envs=("PAGERDUTY_API_KEY",),
        seeds=(
            "escalation policy sbx-<n>-oncall over the shared bot user",
            "service sbx-<n>-checkout",
            "one incident triggered through Events API v2, dedup key sbx-<n>-seed-1",
        ),
        cost_note="PagerDuty free plan caps at 5 users; every environment shares one bot user.",
    ),
    SandboxConnector(
        key="sentry",
        tier="A",
        status="pending",
        provisioner="bridge:jianyuan/sentry",
        tenant="sentry-sandbox-org",
        prefix_scope="project slugs: sbx-<n>",
        envs=(
            "SENTRY_AUTH_TOKEN",
            "SENTRY_ORG",
            "SENTRY_BASE_URL",
        ),
        seeds=(
            "team + project sbx-<n>",
            (
                "errors sent to the DSN with a UNIQUE FINGERPRINT per run — Sentry groups by fingerprint and a repeat "
                "does not reset firstSeen, which is what the window filters on"
            ),
        ),
        cost_note="free tier is 5k errors/month; cap the seeder so a loop cannot burn it.",
    ),
    SandboxConnector(
        key="slack",
        tier="A",
        status="pending",
        provisioner="bridge:pablovarela/slack",
        tenant="slack-sandbox-workspace",
        prefix_scope="channel names: sbx-<n>-*",
        envs=(
            "SLACK_WEBHOOK_URL",
            "SLACK_BOT_TOKEN",
        ),
        seeds=(
            "channel sbx-<n>-ops",
            "messages, a thread, and a reaction",
        ),
        cost_note=(
            "slack is NOT in LEGACY_VERIFY_KINDS and has no probe at all, so this row asserts through "
            "tools/slack.py::auth_test directly. Free workspaces retain 90 days, ample for a 14d window."
        ),
    ),
    SandboxConnector(
        key="statuspage",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="statuspage-sandbox-page",
        prefix_scope="incident titles: sbx-<n> ...",
        envs=(
            "STATUSPAGE_API_KEY",
            "STATUSPAGE_PAGE_ID",
        ),
        seeds=(
            "one component sbx-<n>",
            "one active incident",
        ),
        cost_note="free plan is a single page, so the page is the tenant and the prefix is the incident title.",
    ),
    SandboxConnector(
        key="trello",
        tier="A",
        status="pending",
        provisioner="seeder",
        tenant="trello-sandbox-account",
        prefix_scope="board names: sbx-<n>",
        envs=(
            "TRELLO_API_KEY",
            "TRELLO_TOKEN",
            "TRELLO_BOARD_ID",
        ),
        seeds=(
            "board sbx-<n>",
            "three lists",
            "cards across lists",
        ),
        cost_note="free; the board is the container, so teardown is deleting it.",
    ),
    SandboxConnector(
        key="azure_cloud",
        tier="B",
        status="pending",
        provisioner="pulumi:pulumi-azure-native",
        tenant="azure-sandbox-subscription",
        prefix_scope="resource groups: sbx-<n>",
        envs=(
            "AZURE_CLOUD_TENANT_ID",
            "AZURE_CLOUD_CLIENT_ID",
            "AZURE_CLOUD_CLIENT_SECRET",
            "AZURE_CLOUD_SUBSCRIPTION_ID",
        ),
        seeds=(
            "a",
            "n",
            " ",
            "a",
            "l",
            "e",
            "r",
            "t",
            " ",
            "r",
            "u",
            "l",
            "e",
            " ",
            "i",
            "n",
            " ",
            "t",
            "h",
            "e",
            " ",
            "e",
            "n",
            "v",
            "i",
            "r",
            "o",
            "n",
            "m",
            "e",
            "n",
            "t",
            "'",
            "s",
            " ",
            "r",
            "e",
            "s",
            "o",
            "u",
            "r",
            "c",
            "e",
            " ",
            "g",
            "r",
            "o",
            "u",
            "p",
        ),
        reason=(
            "needs a third cloud subscription with real spend, and a subscription cannot be created per environment."
        ),
        promote_when="a funded sandbox subscription exists.",
        cost_note="pay-as-you-go.",
    ),
    SandboxConnector(
        key="datadog",
        tier="B",
        status="pending",
        provisioner="pulumi:pulumi-datadog",
        tenant="datadog-sandbox-org",
        prefix_scope="monitor names sbx-<n>-* and the tag env:sbx-<n>",
        envs=(
            "DATADOG_API_KEY",
            "DATADOG_APP_KEY",
            "DATADOG_SITE",
        ),
        seeds=(
            "monitor sbx-<n>-checkout on a custom metric",
            "a metric value over threshold, so Datadog raises a genuine monitor alert",
        ),
        reason=(
            "the fetcher filters sources=alert, so a posted event never appears — the seed must drive a real monitor, "
            "and the monitor API is not on the free plan."
        ),
        promote_when="a Datadog plan with the monitor API is bought (~$15/host/month).",
        cost_note="14-day trial, then paid.",
    ),
    SandboxConnector(
        key="elevenlabs",
        tier="B",
        status="pending",
        provisioner="seeder",
        tenant="elevenlabs-sandbox-account",
        prefix_scope="",
        envs=("ELEVENLABS_API_KEY",),
        reason=(
            "yeaboi gives it no fetch() — config and a GET /v1/user probe are the entire surface, so there are no "
            "per-environment resources for an id to prefix."
        ),
        promote_when="never; this row is complete as it is.",
        cost_note="free tier.",
    ),
    SandboxConnector(
        key="gcp",
        tier="B",
        status="pending",
        provisioner="pulumi:pulumi-gcp",
        tenant="gcp-sandbox-project",
        prefix_scope="labels: env=sbx-<n>",
        envs=(
            "GCP_AUTH_METHOD",
            "GCP_PROJECT_ID",
            "GCP_SERVICE_ACCOUNT",
        ),
        seeds=(
            "a",
            " ",
            "f",
            "u",
            "n",
            "c",
            "t",
            "i",
            "o",
            "n",
            " ",
            "t",
            "h",
            "a",
            "t",
            " ",
            "t",
            "h",
            "r",
            "o",
            "w",
            "s",
            ",",
            " ",
            "s",
            "o",
            " ",
            "E",
            "r",
            "r",
            "o",
            "r",
            " ",
            "R",
            "e",
            "p",
            "o",
            "r",
            "t",
            "i",
            "n",
            "g",
            " ",
            "h",
            "a",
            "s",
            " ",
            "a",
            " ",
            "g",
            "r",
            "o",
            "u",
            "p",
        ),
        reason=(
            "GCP_SERVICE_ACCOUNT wants a long-lived JSON key blob, the worst credential shape in the 28, and project "
            "creation is not per-environment automatable on the free tier."
        ),
        promote_when="Workload Identity Federation from the GitHub OIDC token replaces the JSON key.",
        cost_note="one long-lived project; environments are label prefixes inside it.",
    ),
    SandboxConnector(
        key="incidentio",
        tier="B",
        status="pending",
        provisioner="seeder",
        tenant="incidentio-sandbox-account",
        prefix_scope="incident names: sbx-<n> ...",
        envs=("INCIDENTIO_API_KEY",),
        seeds=(
            "i",
            "n",
            "c",
            "i",
            "d",
            "e",
            "n",
            "t",
            "s",
            " ",
            "c",
            "r",
            "e",
            "a",
            "t",
            "e",
            "d",
            " ",
            "b",
            "y",
            " ",
            "h",
            "a",
            "n",
            "d",
            ",",
            " ",
            "o",
            "n",
            "c",
            "e",
        ),
        reason="no usable free tier; a sandbox account is a paid seat, so nothing can be seeded per run.",
        promote_when="a sandbox subscription exists — then bridge the official incident-io/incident provider.",
        cost_note="the most likely row to be demoted to C if the spend is refused.",
    ),
    SandboxConnector(
        key="jsm_ops",
        tier="B",
        status="pending",
        provisioner="seeder",
        tenant="atlassian-site-yeaboi-sbx",
        prefix_scope="alert message prefix: sbx-<n>",
        envs=(
            "JSM_OPS_API_KEY",
            "JSM_OPS_CLOUD_ID",
        ),
        seeds=(
            "a",
            "l",
            "e",
            "r",
            "t",
            "s",
            " ",
            "c",
            "r",
            "e",
            "a",
            "t",
            "e",
            "d",
            " ",
            "b",
            "y",
            " ",
            "h",
            "a",
            "n",
            "d",
            ",",
            " ",
            "o",
            "n",
            "c",
            "e",
        ),
        reason="the Ops alert surface needs a JSM Premium site; the free Jira site has nothing to seed.",
        promote_when="a Premium JSM site is funded; alerts are then API-creatable with an integration key.",
        cost_note="shares JSM_OPS_CLOUD_ID with the Jira site — same Atlassian tenant.",
    ),
    SandboxConnector(
        key="tavus",
        tier="B",
        status="pending",
        provisioner="seeder",
        tenant="tavus-sandbox-account",
        prefix_scope="",
        envs=("TAVUS_API_KEY",),
        reason="same shape as elevenlabs — verify-only, nothing to seed — and no meaningful free tier.",
        promote_when="never; this row is complete as it is.",
        cost_note="trial keys expire, so this is the most likely secret to go stale. Rotate every 30 days.",
    ),
    SandboxConnector(
        key="apple_music",
        tier="C",
        status="pending",
        provisioner="none",
        tenant="",
        prefix_scope="",
        envs=("APPLE_MUSIC_PLAYBACK",),
        reason=(
            "there is no server. library_apple.py shells osascript at the local Music.app, so there is no tenant to "
            "create and no HTTP to record. Covered by a fake osascript on PATH asserting the AppleScript yeaboi emits."
        ),
        cost_note="macOS-only, so it runs in the nightly and in local `make test`, never on a Linux runner.",
    ),
    SandboxConnector(
        key="spotify",
        tier="C",
        status="pending",
        provisioner="none",
        tenant="",
        prefix_scope="",
        envs=(
            "SPOTIFY_PLAYBACK",
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_REFRESH_TOKEN",
            "SPOTIFY_ACCOUNT",
        ),
        reason=(
            "SPOTIFY_REFRESH_TOKEN is minted by an interactive loopback OAuth sign-in (connectors/oauth.py, "
            "callback on 127.0.0.1). There is no tenant to create, and the token is tied to one "
            "person's music account, which "
            "cannot be shared with CI."
        ),
        cost_note="cassette lane only, and never exercise the put_json playback write.",
    ),
    SandboxConnector(
        key="youtube_music",
        tier="C",
        status="pending",
        provisioner="none",
        tenant="",
        prefix_scope="",
        envs=(
            "YOUTUBE_MUSIC_PLAYBACK",
            "YOUTUBE_MUSIC_CLIENT_ID",
            "YOUTUBE_MUSIC_CLIENT_SECRET",
            "YOUTUBE_MUSIC_REFRESH_TOKEN",
            "YOUTUBE_MUSIC_ACCOUNT",
        ),
        reason=(
            "same interactive Google OAuth as spotify, and worse: a refresh token for an OAuth app in Testing "
            "publishing status expires after 7 days."
        ),
        cost_note="cassette lane only until the OAuth app is published and verified.",
    ),
)


def by_key(key: str) -> SandboxConnector | None:
    return next((r for r in SANDBOX_ROWS if r.key == key), None)


def keys() -> frozenset[str]:
    return frozenset(r.key for r in SANDBOX_ROWS)
