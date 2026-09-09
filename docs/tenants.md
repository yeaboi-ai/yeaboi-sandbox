# The tenants

One hand-made tenant per vendor. **No sandbox tenant may share an identity, an account, an
organisation or a token with a production tenant** — that is the rule everything else rests on.

Two vendors get this wrong by default and force the shape of the whole thing:

- **Atlassian.** An API token minted at `id.atlassian.com` is scoped to the *user*, not the site. If
  the sandbox Jira and the company Jira are reachable by the same Atlassian account, the token works
  on both. A dedicated Atlassian account on a dedicated email alias is mandatory.
- **GitHub.** A classic PAT is user-scoped and sees every org the user is in; even a fine-grained
  one scoped to `yeaboi-ai` sees production. So the GitHub sandbox is **its own organisation**,
  `yeaboi-sandbox`. `CIRCLECI_ORG_SLUG` names a VCS org, so CircleCI forces the same conclusion.

Fill this table as tenants are created. `sbx doctor` fails 14 days before any dated cell.

| Vendor | Tenant | Owner | Plan | Monthly | Credential expires | Notes |
|---|---|---|---|---|---|---|
| pagerduty | | | free (5 users) | $0 | | one shared bot user across every environment |
| github | `yeaboi-sandbox` org | | free | $0 | n/a | GitHub App, 1-hour installation token per run |
| atlassian | one site, serves jira + confluence + jsm_ops | | free | $0 | | dedicated account + email alias |
| aws | separate account, not the telemetry one | | — | ~$5 | n/a | Identity Center + OIDC, no static keys |
| jenkins | self-hosted on AWS | | — | $15–30 | n/a | the only vendor with no vendor; needs public HTTPS |
| datadog | | | **paid** | ~$15 | | the free plan has no monitor API — tier B until bought |
| incidentio | | | **paid** | ? | | no free tier; most likely demotion to C |

## Rotation

Where a vendor supports short-lived credentials, store no PAT at all — GitHub App installation
tokens, GitLab project access tokens, an Entra service principal for Azure DevOps, Workload Identity
Federation for GCP. For the rest, rotation is a nag with teeth: `yeaboi:rotation-days` on the
Secrets Manager entry, advisory at 80%, red at 100%.

This is acceptable because these tokens are worthless — they reach an empty tenant full of fake
data. The interval bounds how long a leak is a nuisance, not how much it costs.
