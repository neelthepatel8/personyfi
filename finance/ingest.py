import json
import logging
import sqlite3
import time
from datetime import date, datetime
from typing import Iterable

from . import db
from .config import Config
from .teller_client import TellerApiError, TellerClient
from . import rules as rules_engine

logger = logging.getLogger(__name__)


class IngestError(RuntimeError):
    pass


def ingest_all(
    config: Config,
    start_date: str | None = None,
    end_date: str | None = None,
    page_size: int = 100,
) -> None:
    conn = db.connect(config.db_path)
    db.init_db(conn)
    client = TellerClient(config)

    db.upsert_item(conn, "teller", None, "teller-env")
    start, end = _parse_date_range(start_date, end_date)
    use_cursor = start is None and end is None
    try:
        accounts = client.list_accounts()
    except TellerApiError as exc:
        raise IngestError(f"Teller accounts failed: {exc}") from exc
    normalized_accounts = [_normalize_account(account) for account in accounts]
    db.upsert_accounts(conn, "teller", normalized_accounts)

    failures: list[str] = []
    for account in accounts:
        account_id = account.get("id")
        if not account_id:
            continue
        try:
            _ingest_account(conn, client, account, start, end, page_size, use_cursor)
        except IngestError as exc:
            logger.error("Account %s ingest failed: %s", account_id, exc)
            failures.append(account_id)

    if failures:
        raise IngestError(f"{len(failures)} accounts failed ingest")


def ingest_one_account(
    config: Config,
    account_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    page_size: int = 100,
) -> None:
    conn = db.connect(config.db_path)
    db.init_db(conn)
    client = TellerClient(config)

    db.upsert_item(conn, "teller", None, "teller-env")
    start, end = _parse_date_range(start_date, end_date)
    use_cursor = start is None and end is None
    account = _find_account(client, account_id)
    if not account:
        raise IngestError(f"Account not found: {account_id}")

    db.upsert_accounts(conn, "teller", [_normalize_account(account)])
    _ingest_account(conn, client, account, start, end, page_size, use_cursor)


def _find_account(client: TellerClient, account_id: str) -> dict | None:
    accounts = client.list_accounts()
    for account in accounts:
        if account.get("id") == account_id:
            return account
    return None


def _ingest_account(
    conn: sqlite3.Connection,
    client: TellerClient,
    account: dict,
    start_date: date | None,
    end_date: date | None,
    page_size: int,
    use_cursor: bool,
) -> None:
    account_id = account["id"]
    last_seen_id = db.get_account_cursor(conn, account_id) if use_cursor else None

    new_transactions: list[dict] = []
    raw_transactions: list[dict] = []
    newest_id: str | None = None

    from_id = None
    reached_cursor = False
    stop_at_older = False
    while True:
        # Context7 (teller_io): GET /accounts/:account_id/transactions supports start_date/end_date,
        # count, and from_id for pagination. We still window locally for safety.
        page = _fetch_transactions_page(
            client,
            account_id,
            page_size,
            from_id,
            start_date,
            end_date,
        )
        if not page:
            break

        if newest_id is None:
            newest_id = page[0].get("id")

        for tx in page:
            tx_id = tx.get("id")
            if last_seen_id and tx_id == last_seen_id:
                reached_cursor = True
                break
            tx_date = _parse_tx_date(tx.get("date"))
            if start_date and tx_date and tx_date < start_date:
                # from_id is ledger-ordered; once older than start_date we can stop.
                stop_at_older = True
                break
            if end_date and tx_date and tx_date > end_date:
                continue
            new_transactions.append(_normalize_transaction(tx, account))
            raw_transactions.append(tx)

        if reached_cursor or stop_at_older:
            break

        if len(page) < page_size:
            break

        from_id = page[-1].get("id")
        if not from_id:
            break

    if new_transactions:
        db.upsert_transactions(conn, "teller", new_transactions)
        _record_raw(conn, "teller", raw_transactions)
        _apply_rules(conn, new_transactions)

    if use_cursor and newest_id:
        db.set_account_cursor(conn, account_id, newest_id)
    else:
        db.touch_account_sync(conn, account_id)

    logger.info(
        "Account %s sync complete. added=%d",
        account_id,
        len(new_transactions),
    )


def _normalize_transaction(tx: dict, account: dict) -> dict:
    details = tx.get("details") or {}
    counterparty = details.get("counterparty") or {}
    status = tx.get("status")
    amount = tx.get("amount")
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0

    return {
        "transaction_id": tx.get("id"),
        "account_id": account.get("id"),
        "name": tx.get("description") or counterparty.get("name") or "",
        "merchant_name": counterparty.get("name"),
        "amount": amount_value,
        "iso_currency_code": account.get("currency"),
        "date": tx.get("date"),
        "authorized_date": None,
        "pending": True if status == "pending" else False,
        "pending_transaction_id": None,
        "category_id": None,
        "category": details.get("category"),
    }


def _normalize_account(account: dict) -> dict:
    return {
        "account_id": account.get("id"),
        "name": account.get("name"),
        "official_name": account.get("name"),
        "type": account.get("type"),
        "subtype": account.get("subtype"),
        "mask": account.get("last_four"),
    }


def _record_raw(conn: sqlite3.Connection, item_id: str, transactions: Iterable[dict]) -> None:
    for tx in transactions:
        payload = json.dumps(tx, sort_keys=True, default=_json_default)
        decision = json.dumps({"status": "unreviewed"}, sort_keys=True)
        tx_id = tx.get("id") or tx.get("transaction_id")
        if not tx_id:
            continue
        db.insert_transaction_raw(conn, item_id, tx_id, payload, decision)


def _apply_rules(conn: sqlite3.Connection, transactions: Iterable[dict]) -> None:
    rules = rules_engine.list_rules(conn)
    if not rules:
        return
    transaction_ids = [
        entry.get("transaction_id") or entry.get("id") for entry in transactions
    ]
    updated = rules_engine.apply_rules_to_transaction_ids(
        conn, rules, transaction_ids, item_id="teller"
    )
    if updated:
        logger.info("Applied %d rules-based categorization updates", updated)


def _json_default(obj: object) -> str:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


def _parse_tx_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _parse_date_range(
    start_date: str | None, end_date: str | None
) -> tuple[date | None, date | None]:
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
    except ValueError as exc:
        raise IngestError("Dates must be in YYYY-MM-DD format") from exc
    if start and end and start > end:
        raise IngestError("start_date must be <= end_date")
    return start, end


def _fetch_transactions_page(
    client: TellerClient,
    account_id: str,
    page_size: int,
    from_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    delay = 2
    for attempt in range(5):
        try:
            return client.list_transactions(
                account_id,
                count=page_size,
                from_id=from_id,
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
            )
        except TellerApiError as exc:
            if exc.status_code in (429, 503, 504) and attempt < 4:
                retry_after = _parse_retry_after(exc.retry_after)
                time.sleep(retry_after or delay)
                delay *= 2
                continue
            raise IngestError(f"Teller transactions failed: {exc}") from exc
    return []


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
