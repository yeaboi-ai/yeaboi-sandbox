# --- shared tooling (yeaboi-tooling, pinned by .tooling-rev) ------------------
#
# Paste this block at the top of the repo's Makefile, verbatim. It clones the
# tooling repo to `.tooling/` at the pinned sha and includes the shared targets
# (wt-*, tooling-*, contracts-*). The clone happens at parse time and only when
# the pin and the checkout disagree, so the steady state is two file reads and
# no network — and a fresh `git worktree add`, which never populates a
# submodule, provisions itself on the first `make`.
#
# Bump the pin with `make tooling-bump` and commit `.tooling-rev`.

TOOLING      := .tooling
TOOLING_REV  := $(shell cat .tooling-rev 2>/dev/null | tr -d '[:space:]')
TOOLING_HAVE := $(shell cat $(TOOLING)/.git/tooling-rev 2>/dev/null | tr -d '[:space:]')

ifeq ($(TOOLING_REV),)
$(error missing .tooling-rev — this repo pins the shared tooling by commit sha)
endif
ifneq ($(TOOLING_REV),$(TOOLING_HAVE))
TOOLING_SYNC := $(shell bash scripts/tooling-sync.sh >&2 && echo ok)
ifneq ($(TOOLING_SYNC),ok)
$(error shared tooling could not be synced — see the [tooling] lines above)
endif
endif

# The include brings targets with it, and the first target in a makefile is the
# default goal. Name the goal explicitly so `make` with no arguments still
# prints help rather than cutting a worktree.
.DEFAULT_GOAL := help

include $(TOOLING)/mk/common.mk

# --- end shared tooling ------------------------------------------------------

UV := $(shell command -v uv 2>/dev/null || echo "$$HOME/.local/bin/uv")

# The connector catalog is generated in yeaboi.ai and vendored here by sha. It is
# the roster the tier registry is held to; never edit contracts/ in this repo.
CONTRACTS_REPO  := https://github.com/yeaboi-ai/yeaboi.ai.git
CONTRACTS_DIR   := .
CONTRACTS_PATHS := contracts/v1/connectors.json

.PHONY: install lint format format-check test test-fast test-scoped ship-gate \
        up down env assert seed live sweep doctor

install: ## Create the venv and install dependencies
	$(UV) sync --all-extras

lint: ## Lint with ruff, and refuse the workflow triggers this repo must never use
	$(UV) run ruff check src/ infra/ tests/
	@! grep -rnE "^[[:space:]]*pull_request_target[[:space:]]*:" .github/workflows/ 2>/dev/null || \
	  { echo "[lint] pull_request_target is banned here: it runs base-branch workflow logic"; \
	    echo "[lint] over head-branch test code that executes with real vendor tokens."; \
	    echo "[lint] Use a GitHub Environment with required reviewers instead."; exit 1; }

format: ## Format with ruff (writes)
	$(UV) run ruff format src/ infra/ tests/
	$(UV) run ruff check --fix src/ infra/ tests/

format-check: ## What CI asserts
	$(UV) run ruff format --check src/ infra/ tests/

# ---------------------------------------------------------------------------
# Hermetic lanes. NOTHING below reaches AWS or a vendor.
#
# workspace.toml marks this repo `vendors = true`, so yeaboi-tooling's nightly
# checks it out on a bare runner with no credentials and runs `make ship-gate`.
# Every live target is therefore OUTSIDE test and ship-gate, deliberately.
# If you are here to add `assert` to `test`: that is the mistake this comment
# exists to stop. `.github/workflows/smoke.yml` in yeaboi.ai is `if: false`
# today for exactly that reason.
# ---------------------------------------------------------------------------
test-fast: ## The unit lane: registry parity, env parity, prefix safety. No network.
	$(UV) run pytest tests/unit

test-scoped: test-fast ## Same as test-fast until there is more than one lane to scope

test: test-fast ## Everything a PR must pass locally (hermetic)

ship-gate: lint format-check test contracts-check tooling-check ## The full local gate

# ---------------------------------------------------------------------------
# Live targets. These cost money and touch real vendor tenants.
# ---------------------------------------------------------------------------
up: ## Provision + seed an environment   (STACK=local-<you>)
	$(UV) run sbx up --stack "$(STACK)"

down: ## Destroy an environment and sweep its prefix
	$(UV) run sbx down --stack "$(STACK)"

env: ## Print the env block as shell exports:  eval "$$(make env STACK=...)"
	@$(UV) run sbx env --stack "$(STACK)"

assert: ## Run the assertions against a provisioned environment (ONLY=<connector>)
	$(UV) run sbx assert --stack "$(STACK)" $(if $(ONLY),--only $(ONLY),)

doctor: ## Tenant fence + credential expiry check for every connector
	$(UV) run sbx doctor --stack "$(STACK)"

sweep: ## Find (and with APPLY=1, delete) resources whose environment is gone
	$(UV) run sbx sweep $(if $(APPLY),--apply,)
