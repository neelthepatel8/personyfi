# Bootstrapping

This repo has a minimal CLI, SQLite schema, and Teller smoke script.

## Setup

- Copy `.env.example` to `.env` and fill in Teller credentials.
- Install dependencies: `pip install -r requirements.txt`.
- Defaults are tuned for a 24x7 loop: ingest every 10 minutes over a 10-day window.

## Commands

- `python -m finance doctor`
  - Verifies env, DB, and Teller connectivity.
- `python -m finance ingest [--account-id ACCOUNT_ID] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--page-size N]`
  - Pulls transactions for all accounts (or a single account) with optional date window and page size.
  - Teller supports `start_date`/`end_date` directly, so use a small window for large accounts.
  - For incremental sync, consider expanding the window by 7-10 days to catch pending-to-posted shifts.
  - If no dates are provided, the CLI uses `FINANCE_INGEST_LOOKBACK_DAYS`.
  - Use `--full` to run a full cursor-based backfill.
- `python -m finance inbox`
  - Lists transactions with unknown merchants (no mapping in `merchant_map`).
- `python -m finance cleanup [--force]`
  - Removes non-Teller records (helpful if old Plaid data exists).
- `python -m finance serve`
  - Runs a local HTTP API and a scheduled ingest loop (default every 10 minutes).
  - Configure via `FINANCE_API_HOST`, `FINANCE_API_PORT`, `FINANCE_INGEST_INTERVAL_MINUTES`, `FINANCE_INGEST_LOOKBACK_DAYS`, `FINANCE_INGEST_PAGE_SIZE`.
  - UI is available at `http://127.0.0.1:3030/` (charts, rules, and transactions).

## Smoke

- `python scripts/teller_smoke.py`
  - Lists accounts, fetches balances, and a first page of transactions.

## API endpoints

- `GET /` (simple UI)
- `GET /health`
- `GET /accounts`
- `GET /transactions?account_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=100&offset=0`
- `GET /insights?account_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /inbox?limit=100`
- `GET /status`
- `GET /rules`
- `POST /ingest` (JSON body: `account_id`, `start_date`, `end_date`, `lookback_days`, `page_size`, `full`)
- `POST /rules` (JSON body: `pattern`, `match_type`, `category`, `merchant`, `priority`)
- `POST /categorize` (JSON body: `account_id`, `start_date`, `end_date`, `lookback_days`, `full`)
