import sqlite3

from . import db


def load_unknown_merchants(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            t.transaction_id,
            t.date,
            t.amount,
            COALESCE(t.merchant_name, t.name) AS raw_name
        FROM transactions t
        LEFT JOIN merchant_map m ON m.raw_name = COALESCE(t.merchant_name, t.name)
        WHERE t.removed = 0
          AND COALESCE(t.merchant_name, t.name) IS NOT NULL
          AND m.id IS NULL
        ORDER BY t.date DESC
        """
    ).fetchall()
    return [
        {
            "transaction_id": row["transaction_id"],
            "date": row["date"],
            "amount": row["amount"],
            "raw_name": row["raw_name"],
        }
        for row in rows
    ]


def run_inbox(db_path: str) -> int:
    conn = db.connect(db_path)
    db.init_db(conn)
    unknown = load_unknown_merchants(conn)
    if not unknown:
        print("Inbox empty. No unknown merchants.")
        return 0

    print(f"Inbox: {len(unknown)} unknown merchants")
    for entry in unknown[:50]:
        print(
            f"{entry['date']} | {entry['amount']:>7.2f} | {entry['raw_name']}"
        )
    if len(unknown) > 50:
        print(f"... {len(unknown) - 50} more")
    return 0
