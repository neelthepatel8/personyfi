# Finance OS (personal-only) — Agent Instructions

Codex: This repo is a **local-first personal finance tracker** optimized for:
- Apple Pay micro-spend + many small checking-account transactions
- subscriptions spread across multiple accounts/cards
- credit card debt payoff visibility
- minimal daily effort via a tiny “Review Inbox” (2 minutes/day)

This is **not** a general-purpose product. It is purposeful, opinionated, and tailored to one user.

---

## Non-negotiables (Security + Privacy)
- NEVER store bank passwords. Only OAuth/tokenized access via an aggregator (Plaid) or CSV import.
- Secrets never committed. Use `.env` locally + commit `.env.example` only.
- Store long-lived tokens in OS keychain when possible (or encrypted local file as fallback).
- No telemetry by default. Keep data local.

---

## Doc freshness requirement (MANDATORY)
When implementing or changing ANY integration that relies on external docs (Plaid API, SDKs, libraries):
1) **Always use Context7 MCP** to pull the latest, version-specific docs and examples.
2) Do not guess endpoint names/params. Do not rely on memory.
3) In your work, paste the relevant Context7 snippets into comments or the PR description for traceability.

(You have Context7 MCP configured. Prompts should include: “use context7”.)

---

## Product: Exact app flow (the behavior we optimize for)

### Nightly automation (default 2:00am local)
1) Ingest new data for each connected Item (Plaid):
   - Use `/transactions/sync` with stored cursor per Item.
   - Persist raw responses and update cursors.
2) Enrichment pipeline:
   - Merchant normalization (descriptor -> canonical merchant)
   - Rules-first categorization; fallback suggestion with confidence
   - Subscription detection + price creep detection
   - Anomaly detection (new merchant, spikes)
3) Write daily aggregates + generate report:
   - `reports/YYYY-MM-DD.html` (static dashboard)
   - `reports/daily-digest.json` (for notifications)
4) Send optional digest notification (email/telegram) containing:
   - yesterday vs baseline spend
   - top spikes
   - new/changed subscriptions
   - link/path to report + inbox count

### Morning “2-minute habit”
- Run: `finance inbox`
- Show ONLY items needing review:
  - new merchant not mapped
  - low-confidence category
  - subscription candidate not confirmed
  - split-needed transactions
- Single-key actions:
  - `c` set category
  - `m` merge merchant -> canonical
  - `r` create/edit rule (pattern -> category/merchant/subscription)
  - `s` mark subscription yes/no
  - `x` split transaction
  - `u` undo last action
- Goal: keep inbox near zero; every action should create a durable rule/merchant mapping.

### Insights (static HTML, no webapp framework)
Must include:
- Calendar heatmap (daily spend)
- Cashflow Sankey (income -> fixed -> debt -> discretionary)
- Treemap (category -> merchant)
- Subscription waterfall + price creep
- “micro-spend” charts (<$10 / <$20 share and count)
- Debt payoff simulator (avalanche vs snowball + interest saved)

No Streamlit. No server required to view the report.

---

## Plaid integration requirements (Correctness-first)
- Prefer `transactions/sync` for incremental updates; store cursor per Item.
- Support multiple Items (BofA, US Bank, etc.) and multiple accounts per Item.
- Implement “doctor” commands so correctness is verifiable without reading code:
  - `finance doctor` (keys present, DB ok, items reachable)
  - `finance plaid status` (per item: last sync time, cursor, counts)
  - `finance reconcile --days 30` (per account totals + missing coverage warnings)
- Persist a provenance trail per transaction:
  - raw fields snapshot + enrichment decision (rule id, confidence, reasons)
- Implement Replay mode:
  - `finance ingest --record` saves raw JSON to `fixtures/`
  - `finance ingest --replay fixtures/...` replays without hitting Plaid

### Isolation smoke scripts (must exist)
Create runnable scripts that validate Plaid independently of the app:
- `scripts/plaid_sandbox_smoke.py`: uses sandbox token creation + exchange + transactions sync
- `scripts/plaid_dev_smoke.py`: verifies configured dev keys, lists items, runs a small sync
These scripts must print a short, human-readable summary and exit non-zero on failure.

---

## Code quality rules (“non-AI-like”)
- Keep it boring: small modules, explicit types, clear names, minimal magic.
- Add docstrings and comments explaining *why* (especially around Plaid edge cases: pending->posted, removed/added behavior).
- Make every command idempotent where possible.
- Write tests for enrichment logic using fixtures (no network).
- Use structured logging with levels; default output should be clean.

---

## Definition of done (for any PR/task)
- `finance doctor` passes
- Unit tests pass (offline)
- Sandbox smoke passes (when keys available)
- Report generates and opens successfully
- A short `docs/` note exists if behavior changed
- you should still run comamnds and test yourself, so that we dont have errors, then ill do final testing=
---

## Suggested repo layout
- `finance/` core package (cli, db, ingest, enrich, report)
- `scripts/` isolated smoke + utilities
- `fixtures/` recorded API responses (gitignored or small curated set)
- `reports/` generated output (gitignored)
- `docs/` architecture + troubleshooting
