# repo-notes — yeaboi-sandbox

The facts `/ship` and `/sync-main` do not hardcode. Keep this short.

## What this repo is

The real vendor tenants yeaboi's 28 connectors are asserted against. It consumes the **released
yeaboi wheel**, never a source tree, and it changes nothing in yeaboi.

## Commit

Pre-commit runs ruff and gitleaks. Use the actual contributing assistant in attribution; omit it when unknown.

## Gate

`make ship-gate` = `lint` → `format-check` → `test` → `contracts-check` → `tooling-check`.

**Everything in the gate is hermetic — no AWS, no vendor.** `workspace.toml` marks this repo
`vendors = true`, so yeaboi-tooling's `nightly.yml` checks it out on a bare runner with no
credentials and runs this gate. `make lint` also greps the workflows and fails on
`pull_request_target`, which would run base-branch workflow logic over head-branch test code that
executes with real vendor tokens.

Live targets (`up`, `down`, `seed`, `assert`, `sweep`, `doctor`) are deliberately outside `test` and
`ship-gate`. Do not move them in.

## The upstream contract

`contracts/v1/connectors.json` is **vendored, never edited here**, pinned by sha in
`.contracts-rev`. A red `test_tier_parity` after a nightly means yeaboi added a connector on `main`:
add the row at `tier="C", status="pending"` with the tracking issue in `reason`, and open the
promotion issue. **Do not widen the parity test.**

`src/yeaboi_sandbox/tiers/registry.py`'s `envs` tuples are generated from yeaboi's descriptors and
held to them by `test_env_parity.py`. Regenerate; never hand-edit.

## Never do

- Never rename or move a module under `infra/env/dynamic/`. Python dynamic providers pickle the
  provider class into stack state, so a rename breaks `destroy` on every existing stack and orphans
  real vendor resources nothing can reap.
- Never close over a secret in a dynamic provider — it is pickled into state.
- Never reuse an environment id. A deleted Jira project key stays reserved for 60 days.
- Never `sbx down` the shared environment (`sbx-1`) without the explicit confirmation.
- Never write a sweeper that deletes by exclusion. Match positively on the `sbx-<n>` prefix.

## After the push

Nothing rewrites the branch. A later push is a plain `git push`.

## Conflict playbook

| Path | Resolution |
|---|---|
| `contracts/v1/connectors.json` | Never hand-merge. Take either side, then `make contracts-sync`. |
| `tiers/registry.py` | Keep both rows; the registry is append-only in tier-then-key order. |
| `.tooling-rev`, `.contracts-rev` | Take the newer sha, then run the matching `*-check`. |

## Unattended lane

None yet — every PR here is hand-shipped while the repo is being built out.
