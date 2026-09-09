# yeaboi-sandbox

The real vendor tenants every yeaboi connector is proved against.

yeaboi ships 28 integrations. Before this repo, 24 of them had no live coverage at all: the
contract tests replay hand-written cassettes against `https://test.atlassian.net`, and
`.github/workflows/smoke.yml` has been `if: false` since it was written. The only way to test a
tracker write path was to create real epics in a real Jira.

One hand-made sandbox tenant per vendor. Pulumi owns everything inside it, namespaced by an
environment id. `sbx up` builds a seeded environment, `sbx assert` runs yeaboi's own
`verify_connection` and `gather()` against it, and compares the normalised `OpsEvent`s to exactly
what was seeded.

**Nothing here changes yeaboi.** It consumes the released wheel and the vendored connector catalog.

## Why real tenants

Severity mapping and timestamp normalisation are the two things a mock can never catch and a real
tenant always will. Building the registry already surfaced three:

- PagerDuty can never emit `severity="critical"` — `connectors/pagerduty.py:87` feeds `urgency`
  (only `high`/`low`) into `clean_severity`.
- Grafana's fetch is a *snapshot* of currently-firing rules, not a history, so its fixture has to be
  an always-firing rule rather than a seeded event.
- Sentry groups by fingerprint, so a re-sent identical event does not reset `firstSeen` and the
  fixture silently ages out of the window.

None of those are visible from a recorded cassette.

## Quick start

```bash
make install
make test          # hermetic: registry parity, env parity, prefix safety. No network.
sbx tiers          # what every connector's sandbox story is
```

Live work needs AWS and the vendor tenants:

```bash
make up     STACK=sbx-17
make assert STACK=sbx-17 ONLY=pagerduty
make down   STACK=sbx-17
```

## The safety property

`YEABOI_HOME` relocates yeaboi's data tree, but **not** its credentials — `config.get_config_dir()`
computes `Path.home()/".yeaboi"` live. Combined with `load_user_config()`'s `override=False`, a
connector the sandbox failed to supply a value for would fall through to your real credential and
hit a production tenant while reporting green.

So `sbx` builds the child environment from an allowlist and sets **every** env var every connector
declares, blanking the ones it has no value for. `tests/unit/test_envblock.py` asserts exactly this,
including that a `GITHUB_TOKEN` exported in your shell cannot reach a run.

## Layout

| Path | What |
|---|---|
| `src/yeaboi_sandbox/tiers/registry.py` | the registry: one row per connector, always all 28 |
| `src/yeaboi_sandbox/envid.py` | the prefix vocabulary teardown safety rests on |
| `src/yeaboi_sandbox/envblock.py` | the isolated environment handed to yeaboi |
| `infra/` | Pulumi, in Python: `base` (shared) and `env` (one stack per environment) |
| `contracts/v1/connectors.json` | vendored from yeaboi.ai by sha; never edited here |

## Tiers

**A** — full IaC, seeded fixtures, exact-data assertions.
**B** — real tenant, one-time manual seed, verification only. Every B row states why, and what
would promote it.
**C** — no tenant can exist. Three rows: `spotify` and `youtube_music` need an interactive OAuth
consent no CI can perform, and `apple_music` has no server at all — it shells `osascript`.

`sbx tiers` prints the current state. `tests/unit/test_tier_parity.py` fails when yeaboi adds a
connector this repo has no row for, in both directions.
