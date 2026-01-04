import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from . import db
from .config import Config

logger = logging.getLogger(__name__)

LLM_PROMPT_VERSION = "v1"
LLM_CATEGORY_TAXONOMY = [
    "rent",
    "housing",
    "utilities",
    "groceries",
    "dining",
    "transportation",
    "fuel",
    "subscriptions",
    "shopping",
    "entertainment",
    "health",
    "insurance",
    "education",
    "travel",
    "income",
    "investment",
    "fees",
    "tax",
    "loan",
    "charity",
    "transfer",
]

# Context7 (openai/openai-python): Chat Completions example with response_format.
# client = OpenAI()
# client.chat.completions.create(
#   model="gpt-4o",
#   messages=[{"role": "user", "content": "Generate a JSON with name and age fields"}],
#   response_format={"type": "json_object"},
# )
LLM_SYSTEM_PROMPT = f"""
You are a finance categorization assistant. Categorize each transaction and detect internal transfers.

Rules:
- Return JSON ONLY.
- Use categories from this taxonomy when possible: {", ".join(LLM_CATEGORY_TAXONOMY)}.
- Assign flow_type as one of: expense, income, transfer.
- Mark internal transfers (savings <-> checking, credit card payments, Zelle/ACH to yourself) as flow_type=transfer.
- If the transaction is a credit card payment or an inter-account transfer, category must be transfer.
- Do not double count: transfers should be excluded from spend.
- Confidence is 0.0 to 1.0.
- If rent is split across multiple payments or descriptors, still label them as rent.
- Use account_name, account_type, description, and merchant together to identify transfers or self-to-self movement.
- Credit accounts often show charges as positive and payments as negative; depository accounts often show outflows as negative.

Output schema:
{{
  "items": [
    {{
      "transaction_id": "string",
      "category": "string",
      "flow_type": "expense|income|transfer",
      "confidence": 0.0,
      "merchant": "string|null",
      "notes": "string"
    }}
  ]
}}
""".strip()


class LlmError(RuntimeError):
    pass


@dataclass(frozen=True)
class LlmLabel:
    transaction_id: str
    category: str
    flow_type: str
    confidence: float
    merchant: str | None
    notes: str | None


def categorize_with_llm(
    conn,
    config: Config,
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
) -> dict:
    if not config.llm_enabled:
        raise LlmError("FINANCE_LLM_ENABLED must be set to enable LLM categorization")
    if not config.openai_api_key:
        raise LlmError("OPENAI_API_KEY is required for LLM categorization")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LlmError(
            "openai package is required. Install via requirements.txt."
        ) from exc

    rows = _load_transactions(conn, account_id, start_date, end_date, limit)
    if not rows:
        return {"updated": 0, "batches": 0, "errors": 0}

    client = OpenAI(api_key=config.openai_api_key)
    batch_size = max(config.llm_max_batch, 1)
    updated = 0
    errors = 0
    batches = 0

    for batch in _chunked(rows, batch_size):
        batches += 1
        payload = {
            "prompt_version": LLM_PROMPT_VERSION,
            "transactions": [_format_transaction(row) for row in batch],
        }
        try:
            labels = _call_llm(client, config.llm_model, payload)
        except Exception as exc:
            errors += 1
            logger.error("LLM categorization failed: %s", exc)
            continue
        updated += _apply_labels(conn, labels, config.llm_model)

    return {"updated": updated, "batches": batches, "errors": errors}


def _load_transactions(
    conn,
    account_id: str | None,
    start_date: str | None,
    end_date: str | None,
    limit: int | None,
) -> list[dict]:
    sql = [
        """
        SELECT t.transaction_id,
               t.amount,
               t.date,
               t.name,
               t.merchant_name,
               t.category,
               t.pending,
               a.name AS account_name,
               a.type AS account_type,
               a.subtype AS account_subtype
        FROM transactions t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE t.removed = 0 AND t.item_id = ?
        """
    ]
    params: list[object] = ["teller"]
    if account_id:
        sql.append("AND t.account_id = ?")
        params.append(account_id)
    if start_date:
        sql.append("AND t.date >= ?")
        params.append(start_date)
    if end_date:
        sql.append("AND t.date <= ?")
        params.append(end_date)
    sql.append("ORDER BY t.date DESC, t.transaction_id DESC")
    if limit:
        sql.append("LIMIT ?")
        params.append(limit)

    return [dict(row) for row in conn.execute(" ".join(sql), params).fetchall()]


def _format_transaction(row: dict) -> dict:
    return {
        "transaction_id": row["transaction_id"],
        "date": row["date"],
        "amount": row["amount"],
        "account_name": row["account_name"],
        "account_type": row["account_type"],
        "account_subtype": row["account_subtype"],
        "merchant": row.get("merchant_name"),
        "description": row.get("name"),
        "teller_category": row.get("category"),
        "pending": bool(row.get("pending")),
    }


def _call_llm(client: Any, model: str, payload: dict) -> list[LlmLabel]:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, default=_json_default)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    items = data.get("items", [])
    labels: list[LlmLabel] = []
    for item in items:
        transaction_id = str(item.get("transaction_id") or "")
        category = str(item.get("category") or "").strip()
        flow_type = str(item.get("flow_type") or "expense").strip().lower()
        confidence = _parse_confidence(item.get("confidence"))
        merchant = (item.get("merchant") or "").strip() or None
        notes = (item.get("notes") or "").strip() or None
        if not transaction_id or not category:
            continue
        labels.append(
            LlmLabel(
                transaction_id=transaction_id,
                category=category,
                flow_type=flow_type,
                confidence=confidence,
                merchant=merchant,
                notes=notes,
            )
        )
    return labels


def _apply_labels(conn, labels: list[LlmLabel], model: str) -> int:
    if not labels:
        return 0
    updated = 0
    now = db.utc_now()
    for label in labels:
        flow_type = _normalize_flow_type(label.flow_type, label.category)
        conn.execute(
            """
            UPDATE transactions
            SET category = ?,
                category_id = ?,
                category_source = ?,
                category_confidence = ?,
                flow_type = ?,
                merchant_name = COALESCE(?, merchant_name),
                updated_at = ?
            WHERE transaction_id = ?
            """,
            (
                label.category,
                "llm",
                "llm",
                label.confidence,
                flow_type,
                label.merchant,
                now,
                label.transaction_id,
            ),
        )
        _update_decision(conn, label, model)
        updated += 1
    conn.commit()
    return updated


def _update_decision(conn, label: LlmLabel, model: str) -> None:
    payload = {
        "status": "categorized",
        "source": "llm",
        "model": model,
        "prompt_version": LLM_PROMPT_VERSION,
        "category": label.category,
        "flow_type": _normalize_flow_type(label.flow_type, label.category),
        "confidence": label.confidence,
        "merchant": label.merchant,
        "notes": label.notes,
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
        (
            json.dumps(payload, sort_keys=True, default=_json_default),
            label.transaction_id,
        ),
    )


def _normalize_flow_type(value: str, category: str | None) -> str:
    if value in {"expense", "income", "transfer"}:
        return value
    if category and "transfer" in category.lower():
        return "transfer"
    return "expense"


def _parse_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(confidence, 1.0))


def _chunked(rows: list[dict], size: int) -> list[list[dict]]:
    return [rows[idx : idx + size] for idx in range(0, len(rows), size)]


def _json_default(obj: object) -> str:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)
