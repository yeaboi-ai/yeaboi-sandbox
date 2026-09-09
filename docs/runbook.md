# Runbook

Operational steps that cannot be automated, in the order they are needed.

---

## 1. Create the GitHub tenant (`yeaboi-sbx`)

The fixture repos (`sbx-17-api` and friends) live in their own organisation. **Not** in `yeaboi-ai`,
and the reason is narrow: GitHub cannot scope *"create a repository"* below an org. Whatever creates
`sbx-17-api` therefore holds org-wide create **and delete**, that credential sits in Secrets Manager
and is read by CI, and `sbx sweep` matches by name prefix. Pointing that at the org holding
yeaboi.ai, yeaboi-frontend, yeaboi-desktop, yeaboi-site and yeaboi-tooling makes a prefix-matching
bug an outage.

This repo — the harness — stays at `yeaboi-ai/yeaboi-sandbox`. Only the throwaway repos move.

### 1a. The organisation

Org creation is **web UI only** on github.com; the REST endpoint (`POST /admin/organizations`) is
GitHub Enterprise Server. So this step is yours.

1. Go to **<https://github.com/organizations/plan>** and choose **Free**.
2. **Organization account name:** `yeaboi-sbx`
3. **Contact email:** prefer a dedicated alias over a personal inbox — this address receives the
   vendor sign-up confirmations for every other sandbox tenant too, and you want them in one place
   that is not your main mail.
4. **This organization belongs to:** *My personal account*.
5. Skip the "invite members" step for now — 1c does it properly.

### 1b. Harden it (Settings, once)

The whole point of this org is that it holds nothing valuable, so lock the surface down:

| Where | Set to | Why |
|---|---|---|
| Settings ▸ Actions ▸ General | **Disable actions** for this organisation | The fixture repos never run CI of their own. Disabling removes the largest remote-execution surface in an org whose token can create repos. |
| Settings ▸ Member privileges ▸ Base permissions | **No permission** | Members get access per repo, not by default. |
| Settings ▸ Member privileges ▸ Repository creation | **Members: off** (owners only) | Only the App and you create repos. |
| Settings ▸ Member privileges ▸ Default repository visibility | **Private** | Fixture data is fake, but there is no reason to index it. GitHub Free gives unlimited private org repos. |
| Settings ▸ Authentication security | **Require two-factor authentication** | Free, and this org's token can delete every repo in it. |

### 1c. Invite your colleague

Settings ▸ People ▸ Invite member → `neakoh`, role **Owner**.

Owner rather than Member: sandbox environments get created and destroyed constantly, and someone who
cannot delete a stuck fixture repo will ask you to, every time.

### 1d. The GitHub App (this is the credential the sandbox actually uses)

**Never a personal access token.** A classic PAT is user-scoped and would see every org you are in,
which is the thing this whole split exists to prevent. An App's installation token is scoped to one
installation and expires in an hour.

Settings ▸ Developer settings ▸ GitHub Apps ▸ **New GitHub App**:

- **Name:** `yeaboi-sbx-provisioner` (must be globally unique; add a suffix if taken)
- **Homepage URL:** `https://github.com/yeaboi-ai/yeaboi-sandbox`
- **Webhook:** uncheck **Active**. Nothing listens.
- **Permissions — Repository:**
  - Administration → **Read and write**  *(needed to delete a repo)*
  - Contents → **Read and write**
  - Issues → **Read and write**
  - Pull requests → **Read and write**
  - Metadata → Read-only *(mandatory, selected for you)*
- **Permissions — Organization:**
  - Administration → **Read and write**  *(this is what `POST /orgs/{org}/repos` requires; repo
    creation genuinely cannot be scoped narrower, which is why the org is separate)*
- **Where can this app be installed:** *Only on this account*

Then **Create GitHub App**, and on the page that follows:

1. Note the **App ID**.
2. **Generate a private key** — it downloads a `.pem` once and never again.
3. **Install App** → `yeaboi-sbx` → **All repositories**.

**"All repositories" is required, not lazy.** An installation scoped to *selected* repositories does
not include repos created afterwards, so every `sbx up` would fail on the repo it just made. It is
safe here precisely because the org contains nothing but throwaway fixtures — which is the same
argument as 1a, arriving a second time.

Note the **Installation ID** from the URL after installing:
`https://github.com/organizations/yeaboi-sbx/settings/installations/<INSTALLATION_ID>`.

### 1e. Hand the key over

Do **not** commit the `.pem` or paste it into a chat. Once AWS step 0 is done:

```bash
aws secretsmanager create-secret \
  --name yeaboi/sandbox/provision/github \
  --secret-string "$(jq -n --arg id "$APP_ID" --arg inst "$INSTALLATION_ID" \
      --rawfile key ~/Downloads/yeaboi-sbx-provisioner.*.private-key.pem \
      '{app_id:$id, installation_id:$inst, private_key:$key}')" \
  --kms-key-id alias/yeaboi-sandbox
shred -u ~/Downloads/yeaboi-sbx-provisioner.*.private-key.pem   # or `rm -P` on macOS
```

Until AWS exists, leave the `.pem` in a password manager and nowhere else.

### 1f. Tell me it is done

```bash
gh api orgs/yeaboi-sbx --jq '{login, plan: .plan.name}'
gh api orgs/yeaboi-sbx/installations --jq '.installations[] | {app_slug, id, repository_selection}'
```

Both answering means the tenant is real, and `docs/tenants.md`'s `github` row can be filled in.

---

## 2. AWS step 0

Not written yet — Identity Center, the `yeaboi-sbx-provisioner` / `yeaboi-sbx-runner` roles, and the
S3 + KMS state backend, replacing the static admin access key currently in use.

## 3. The remaining tenants

One per vendor, tracked in `docs/tenants.md`. PagerDuty first: it is the vertical slice.
