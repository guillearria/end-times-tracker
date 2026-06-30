# end-times-tracker

A living, fully-automated, **fact-based** tracker of possible threats to humanity — where every
published figure is grounded in an official, authoritative source.

It is explicitly **an aggregation of authoritative figures, not a forecast.**

## How it works

The dataset is curated by **Claude Code running on a Claude Max subscription** (no per-token API
spend): it researches threats with web search, drafts cited claims, and runs each record through the
project's deterministic Python trust gate, which decides what publishes. Updates land via a
human-reviewed PR — see the `/refresh-threats` command and `scripts/author_threat.py`. The site
redeploys automatically on merge.

A four-stage pipeline of **independent** Claude *API* calls (Generate → Verify → Clean-up → Optimize)
also exists as an **optional, manual path** (`python -m pipeline.run`); it spends API credits and is
no longer run on a schedule. Either way the same gate enforces the trust model. The four stages:

1. **Generate** (Opus) proposes candidate threats and claims — everything it emits is `unverified`.
2. **Verify** (Opus) grounds each claim against authoritative sources via web search, then a
   deterministic **quarantine gate** (pure Python) checks every citation against a domain allowlist.
   A record publishes only with ≥1 verified claim and no disputed claims; otherwise it is quarantined.
3. **Clean-up** (Haiku) normalizes mechanically — no factual changes.
4. **Optimize** (Sonnet) tightens presentation and computes ranking. A guard asserts it never alters claims.

**Git is the database, the changelog, and the audit trail** — one JSON file per threat, so diffs are
the record of what changed. The frontend is static vanilla HTML/CSS/JS with no build step.

The full design is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Trust model

- Every published claim links its source. A claim is `verified` only when its citation resolves to an
  allowlisted authoritative domain (USGS, WHO, IPCC, NASA/CNEOS, IAEA, CDC, NOAA, UN, NIST, …) — the
  check is a deterministic Python domain match, never the model's say-so.
- Threats that fail verification are **not hidden**: they appear in an "Under review" section, clearly
  flagged as unverified, and are never presented as confirmed.
- Known limit (MVP): verification confirms that an authoritative source was *cited*, not deep semantic
  entailment that the source supports the claim. The `disputed`/`partial` statuses give reviewers a hook.

## Run it locally

```sh
pip install -e ".[dev]"

python -m pipeline.run --dry-run        # full pipeline, deterministic fixtures, $0
pytest                                  # unit tests
python scripts/validate_data.py         # schema validation (the CI hard gate)
python scripts/build_frontend.py        # build frontend/data/threats.json
python scripts/serve_frontend.py        # preview at http://localhost:8000

# One real threat against the live API (needs ANTHROPIC_API_KEY) — the cheap smoke test:
python -m pipeline.run --only-slug yellowstone-supervolcano
```

Curate without spending API credits — drive Claude Code on your Max plan:

```sh
# In a Claude Code session: research + verify threats and open a PR ($0 API)
/refresh-threats nuclear winter, antibiotic resistance

# Or finalize a hand-drafted record through the same deterministic gate:
python scripts/author_threat.py draft.json
```

The API pipeline (`.github/workflows/pipeline.yml`) is **manual-only** (`workflow_dispatch`) and
needs `ANTHROPIC_API_KEY` in the repo's Actions secrets; it spends credits, so the daily cron was
removed. Re-add a `schedule:` trigger there only if you fund the API.

## How to read a threat file

Each `data/threats/<slug>.json` validates against `data/schema/threat.schema.json`:

- `assessment` — categorical `probability.estimate` (+ optional published `numeric_annual`), `severity`,
  `timeframe`, one-line `summary`.
- `claims[]` — each a checkable assertion with `source_name`, `source_url`, `retrieved_date`, and a
  per-claim `verification_status`.
- `verification` — overall `status` (verified / partial / quarantined / unverified) + `confidence`.
- `provenance` — append-only record of which layer last touched it, capped so files stay small.
- `sort_keys` — numeric ordering computed by Optimize.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) to add a threat by hand or propose a new authoritative source.
