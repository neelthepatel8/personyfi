import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from . import db


@dataclass(frozen=True)
class Rule:
    id: int
    pattern: str
    match_type: str
    category: str
    merchant: str | None
    priority: int
    active: bool


@dataclass(frozen=True)
class RuleMatch:
    rule_id: int
    category: str
    merchant: str | None


def list_rules(conn) -> list[Rule]:
    rows = conn.execute(
        """
        SELECT id, pattern, match_type, category, merchant, priority, active
        FROM rules
        ORDER BY priority DESC, id ASC
        """
    ).fetchall()
    return [
        Rule(
            id=row["id"],
            pattern=row["pattern"],
            match_type=row["match_type"],
            category=row["category"],
            merchant=row["merchant"],
            priority=row["priority"],
            active=bool(row["active"]),
        )
        for row in rows
    ]


def create_rule(
    conn,
    pattern: str,
    match_type: str,
    category: str,
    merchant: str | None,
    priority: int,
) -> Rule:
    now = db.utc_now()
    conn.execute(
        """
        INSERT INTO rules (pattern, match_type, category, merchant, priority, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (pattern, match_type, category, merchant, priority, now, now),
    )
    conn.commit()
    rule_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()[0]
    return Rule(
        id=rule_id,
        pattern=pattern,
        match_type=match_type,
        category=category,
        merchant=merchant,
        priority=priority,
        active=True,
    )


def match_rule(merchant: str | None, description: str | None, rules: Iterable[Rule]) -> RuleMatch | None:
    haystack = " ".join([part for part in [merchant, description] if part])
    if not haystack:
        return None
    haystack_lower = haystack.lower()
    for rule in rules:
        if not rule.active:
            continue
        if rule.match_type == "contains":
            if rule.pattern.lower() in haystack_lower:
                return RuleMatch(rule_id=rule.id, category=rule.category, merchant=rule.merchant)
        elif rule.match_type == "regex":
            if re.search(rule.pattern, haystack, re.IGNORECASE):
                return RuleMatch(rule_id=rule.id, category=rule.category, merchant=rule.merchant)
    return None


def apply_rules_to_transactions(
    conn,
    rules: list[Rule],
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    sql = [
        "SELECT transaction_id, name, merchant_name, date FROM transactions",
        "WHERE removed = 0 AND item_id = ?",
    ]
    params: list[object] = ["teller"]
    if account_id:
        sql.append("AND account_id = ?")
        params.append(account_id)
    if start_date:
        sql.append("AND date >= ?")
        params.append(start_date)
    if end_date:
        sql.append("AND date <= ?")
        params.append(end_date)

    rows = conn.execute(" ".join(sql), params).fetchall()
    updated = 0
    now = db.utc_now()
    for row in rows:
        rule_match = match_rule(row["merchant_name"], row["name"], rules)
        if not rule_match:
            continue
        conn.execute(
            """
            UPDATE transactions
            SET category = ?, category_id = ?, merchant_name = COALESCE(?, merchant_name),
                category_source = ?, category_confidence = ?, updated_at = ?
            WHERE transaction_id = ?
            """,
            (
                rule_match.category,
                str(rule_match.rule_id),
                rule_match.merchant,
                "rule",
                1.0,
                now,
                row["transaction_id"],
            ),
        )
        _update_decision(conn, row["transaction_id"], rule_match)
        updated += 1

    conn.commit()
    return updated


def apply_rules_to_transaction_ids(
    conn,
    rules: list[Rule],
    transaction_ids: Iterable[str],
    item_id: str = "teller",
) -> int:
    ids = [value for value in transaction_ids if value]
    if not ids or not rules:
        return 0

    updated = 0
    now = db.utc_now()
    for chunk in _chunked(ids, 200):
        placeholders = ",".join(["?"] * len(chunk))
        params: list[object] = [item_id, *chunk]
        rows = conn.execute(
            f"""
            SELECT transaction_id, name, merchant_name
            FROM transactions
            WHERE item_id = ? AND transaction_id IN ({placeholders})
            """,
            params,
        ).fetchall()
        for row in rows:
            rule_match = match_rule(row["merchant_name"], row["name"], rules)
            if not rule_match:
                continue
            conn.execute(
                """
                UPDATE transactions
                SET category = ?, category_id = ?, merchant_name = COALESCE(?, merchant_name),
                    category_source = ?, category_confidence = ?, updated_at = ?
                WHERE transaction_id = ?
                """,
                (
                    rule_match.category,
                    str(rule_match.rule_id),
                    rule_match.merchant,
                    "rule",
                    1.0,
                    now,
                    row["transaction_id"],
                ),
            )
            _update_decision(conn, row["transaction_id"], rule_match)
            updated += 1

    conn.commit()
    return updated


def _update_decision(conn, transaction_id: str, rule_match: RuleMatch) -> None:
    payload = {
        "status": "categorized",
        "rule_id": rule_match.rule_id,
        "category": rule_match.category,
        "merchant": rule_match.merchant,
        "source": "rule",
        "updated_at": datetime.utcnow().isoformat(),
    }
    conn.execute(
        """
        UPDATE transaction_raw
        SET decision_json = ?
        WHERE id = (
            SELECT id FROM transaction_raw
            WHERE transaction_id = ?
            ORDER BY id DESC
            LIMIT 1
        )
        """,
        (json_dumps(payload), transaction_id),
    )


def json_dumps(payload: dict) -> str:
    def _default(obj: object) -> str:
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return str(obj)

    import json

    return json.dumps(payload, sort_keys=True, default=_default)


def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]
