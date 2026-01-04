import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class ItemRecord:
    item_id: str
    institution_id: str | None
    access_token_key: str
    cursor: str | None
    status: str
    last_sync_at: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            item_id TEXT NOT NULL UNIQUE,
            institution_id TEXT,
            access_token_key TEXT NOT NULL,
            cursor TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            last_sync_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            item_id TEXT NOT NULL,
            account_id TEXT NOT NULL UNIQUE,
            name TEXT,
            official_name TEXT,
            type TEXT,
            subtype TEXT,
            mask TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(item_id)
        );

        CREATE TABLE IF NOT EXISTS account_sync (
            account_id TEXT PRIMARY KEY,
            last_transaction_id TEXT,
            last_sync_at TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            transaction_id TEXT NOT NULL UNIQUE,
            item_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            name TEXT NOT NULL,
            merchant_name TEXT,
            amount REAL NOT NULL,
            iso_currency_code TEXT,
            date TEXT NOT NULL,
            authorized_date TEXT,
            pending INTEGER NOT NULL,
            pending_transaction_id TEXT,
            category_id TEXT,
            category TEXT,
            removed INTEGER NOT NULL DEFAULT 0,
            removed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(item_id)
        );

        CREATE TABLE IF NOT EXISTS transaction_raw (
            id INTEGER PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            decision_json TEXT,
            FOREIGN KEY(item_id) REFERENCES items(item_id)
        );

        CREATE TABLE IF NOT EXISTS merchant_map (
            id INTEGER PRIMARY KEY,
            raw_name TEXT NOT NULL UNIQUE,
            canonical_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY,
            pattern TEXT NOT NULL,
            match_type TEXT NOT NULL,
            category TEXT NOT NULL,
            merchant TEXT,
            priority INTEGER NOT NULL DEFAULT 100,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_item_id ON transactions(item_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_pending ON transactions(pending);
        CREATE INDEX IF NOT EXISTS idx_transaction_raw_item_id ON transaction_raw(item_id);
        CREATE INDEX IF NOT EXISTS idx_rules_priority ON rules(priority);
        """
    )
    _ensure_column(conn, "transactions", "flow_type", "TEXT")
    _ensure_column(conn, "transactions", "category_source", "TEXT")
    _ensure_column(conn, "transactions", "category_confidence", "REAL")
    conn.commit()


def upsert_item(
    conn: sqlite3.Connection,
    item_id: str,
    institution_id: str | None,
    access_token_key: str,
) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO items (item_id, institution_id, access_token_key, cursor, status, last_sync_at, created_at, updated_at)
        VALUES (?, ?, ?, NULL, 'active', NULL, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            institution_id=excluded.institution_id,
            access_token_key=excluded.access_token_key,
            updated_at=excluded.updated_at
        """,
        (item_id, institution_id, access_token_key, now, now),
    )
    conn.commit()


def update_item_cursor(
    conn: sqlite3.Connection,
    item_id: str,
    cursor: str,
    last_sync_at: str | None,
) -> None:
    now = utc_now()
    conn.execute(
        """
        UPDATE items
        SET cursor = ?, last_sync_at = ?, updated_at = ?
        WHERE item_id = ?
        """,
        (cursor, last_sync_at, now, item_id),
    )
    conn.commit()


def list_items(conn: sqlite3.Connection) -> list[ItemRecord]:
    rows = conn.execute(
        """
        SELECT item_id, institution_id, access_token_key, cursor, status, last_sync_at
        FROM items
        ORDER BY item_id
        """
    ).fetchall()
    return [
        ItemRecord(
            item_id=row["item_id"],
            institution_id=row["institution_id"],
            access_token_key=row["access_token_key"],
            cursor=row["cursor"],
            status=row["status"],
            last_sync_at=row["last_sync_at"],
        )
        for row in rows
    ]


def get_item(conn: sqlite3.Connection, item_id: str) -> ItemRecord | None:
    row = conn.execute(
        """
        SELECT item_id, institution_id, access_token_key, cursor, status, last_sync_at
        FROM items
        WHERE item_id = ?
        """,
        (item_id,),
    ).fetchone()
    if row is None:
        return None
    return ItemRecord(
        item_id=row["item_id"],
        institution_id=row["institution_id"],
        access_token_key=row["access_token_key"],
        cursor=row["cursor"],
        status=row["status"],
        last_sync_at=row["last_sync_at"],
    )


def upsert_accounts(conn: sqlite3.Connection, item_id: str, accounts: Iterable[dict]) -> None:
    now = utc_now()
    for account in accounts:
        mask = account.get("mask") or account.get("last_four")
        conn.execute(
            """
            INSERT INTO accounts (
                item_id, account_id, name, official_name, type, subtype, mask, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                item_id=excluded.item_id,
                name=excluded.name,
                official_name=excluded.official_name,
                type=excluded.type,
                subtype=excluded.subtype,
                mask=excluded.mask,
                updated_at=excluded.updated_at
            """,
            (
                item_id,
                account.get("account_id"),
                account.get("name"),
                account.get("official_name"),
                account.get("type"),
                account.get("subtype"),
                mask,
                now,
                now,
            ),
        )
    conn.commit()


def upsert_transactions(conn: sqlite3.Connection, item_id: str, transactions: Iterable[dict]) -> None:
    now = utc_now()
    for transaction in transactions:
        conn.execute(
            """
            INSERT INTO transactions (
                transaction_id, item_id, account_id, name, merchant_name, amount, iso_currency_code,
                date, authorized_date, pending, pending_transaction_id, category_id, category,
                flow_type, category_source, category_confidence,
                removed, removed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            ON CONFLICT(transaction_id) DO UPDATE SET
                item_id=excluded.item_id,
                account_id=excluded.account_id,
                name=excluded.name,
                merchant_name=excluded.merchant_name,
                amount=excluded.amount,
                iso_currency_code=excluded.iso_currency_code,
                date=excluded.date,
                authorized_date=excluded.authorized_date,
                pending=excluded.pending,
                pending_transaction_id=excluded.pending_transaction_id,
                category_id=CASE
                    WHEN transactions.category_source IN ('rule', 'llm') THEN transactions.category_id
                    ELSE excluded.category_id
                END,
                category=CASE
                    WHEN transactions.category_source IN ('rule', 'llm') THEN transactions.category
                    ELSE excluded.category
                END,
                flow_type=CASE
                    WHEN transactions.category_source IN ('rule', 'llm') THEN transactions.flow_type
                    ELSE excluded.flow_type
                END,
                category_source=CASE
                    WHEN transactions.category_source IN ('rule', 'llm') THEN transactions.category_source
                    ELSE excluded.category_source
                END,
                category_confidence=CASE
                    WHEN transactions.category_source IN ('rule', 'llm') THEN transactions.category_confidence
                    ELSE excluded.category_confidence
                END,
                removed=0,
                removed_at=NULL,
                updated_at=excluded.updated_at
            """,
            (
                transaction.get("transaction_id"),
                item_id,
                transaction.get("account_id"),
                transaction.get("name"),
                transaction.get("merchant_name"),
                transaction.get("amount"),
                transaction.get("iso_currency_code"),
                transaction.get("date"),
                transaction.get("authorized_date"),
                1 if transaction.get("pending") else 0,
                transaction.get("pending_transaction_id"),
                transaction.get("category_id"),
                _serialize_category(transaction.get("category")),
                transaction.get("flow_type"),
                transaction.get("category_source"),
                transaction.get("category_confidence"),
                now,
                now,
            ),
        )
    conn.commit()


def mark_removed_transactions(conn: sqlite3.Connection, removed_ids: Iterable[str]) -> None:
    now = utc_now()
    for transaction_id in removed_ids:
        conn.execute(
            """
            UPDATE transactions
            SET removed = 1, removed_at = ?, updated_at = ?
            WHERE transaction_id = ?
            """,
            (now, now, transaction_id),
        )
    conn.commit()


def insert_transaction_raw(
    conn: sqlite3.Connection,
    item_id: str,
    transaction_id: str,
    payload_json: str,
    decision_json: str | None,
) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO transaction_raw (transaction_id, item_id, fetched_at, payload_json, decision_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (transaction_id, item_id, now, payload_json, decision_json),
    )
    conn.commit()


def get_account_cursor(conn: sqlite3.Connection, account_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT last_transaction_id
        FROM account_sync
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()
    if row is None:
        return None
    return row["last_transaction_id"]


def set_account_cursor(conn: sqlite3.Connection, account_id: str, last_transaction_id: str) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO account_sync (account_id, last_transaction_id, last_sync_at)
        VALUES (?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            last_transaction_id=excluded.last_transaction_id,
            last_sync_at=excluded.last_sync_at
        """,
        (account_id, last_transaction_id, now),
    )
    conn.commit()


def touch_account_sync(conn: sqlite3.Connection, account_id: str) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO account_sync (account_id, last_transaction_id, last_sync_at)
        VALUES (?, NULL, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            last_sync_at=excluded.last_sync_at
        """,
        (account_id, now),
    )
    conn.commit()


def cleanup_non_item(
    conn: sqlite3.Connection,
    keep_item_id: str,
    dry_run: bool = True,
) -> dict[str, int]:
    counts = {
        "transaction_raw": conn.execute(
            "SELECT COUNT(*) FROM transaction_raw WHERE item_id != ?",
            (keep_item_id,),
        ).fetchone()[0],
        "transactions": conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE item_id != ?",
            (keep_item_id,),
        ).fetchone()[0],
        "accounts": conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE item_id != ?",
            (keep_item_id,),
        ).fetchone()[0],
        "items": conn.execute(
            "SELECT COUNT(*) FROM items WHERE item_id != ?",
            (keep_item_id,),
        ).fetchone()[0],
        "account_sync": conn.execute(
            """
            SELECT COUNT(*)
            FROM account_sync
            WHERE account_id NOT IN (
                SELECT account_id FROM accounts WHERE item_id = ?
            )
            """,
            (keep_item_id,),
        ).fetchone()[0],
    }

    if dry_run:
        return counts

    conn.execute("DELETE FROM transaction_raw WHERE item_id != ?", (keep_item_id,))
    conn.execute("DELETE FROM transactions WHERE item_id != ?", (keep_item_id,))
    conn.execute("DELETE FROM accounts WHERE item_id != ?", (keep_item_id,))
    conn.execute(
        """
        DELETE FROM account_sync
        WHERE account_id NOT IN (
            SELECT account_id FROM accounts WHERE item_id = ?
        )
        """,
        (keep_item_id,),
    )
    conn.execute("DELETE FROM items WHERE item_id != ?", (keep_item_id,))
    conn.commit()
    return counts


def _serialize_category(category: object | None) -> str | None:
    if category is None:
        return None
    if isinstance(category, list):
        return ",".join([str(entry) for entry in category])
    return str(category)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column in columns:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
