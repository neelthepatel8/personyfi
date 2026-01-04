from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class InsightTotals:
    income: float
    spend: float
    net: float


DEBT_CATEGORIES = {"loan"}
FIXED_CATEGORIES = {
    "utilities",
    "insurance",
    "phone",
    "home",
    "education",
    "health",
    "tax",
    "transport",
    "transportation",
    "groceries",
}


def build_insights(
    conn,
    start_date: str | None,
    end_date: str | None,
    account_id: str | None = None,
) -> dict:
    sql = [
        """
        SELECT t.amount,
               t.date,
               t.category,
               t.merchant_name,
               t.name,
               a.type AS account_type
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

    rows = conn.execute(" ".join(sql), params).fetchall()

    daily_amounts: dict[str, float] = defaultdict(float)
    daily_counts: dict[str, int] = defaultdict(int)
    category_totals: dict[str, float] = defaultdict(float)
    merchant_totals: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    bucket_totals: dict[str, float] = defaultdict(float)
    top_merchants: dict[str, float] = defaultdict(float)

    spend_total = 0.0
    income_total = 0.0
    spend_count = 0
    micro_10_count = 0
    micro_20_count = 0
    micro_10_amount = 0.0
    micro_20_amount = 0.0

    for row in rows:
        amount = float(row["amount"] or 0.0)
        outflow, inflow = _split_flow(amount, row["account_type"])
        if inflow > 0:
            income_total += inflow
        if outflow <= 0:
            continue

        spend_total += outflow
        spend_count += 1
        date_value = row["date"]
        daily_amounts[date_value] += outflow
        daily_counts[date_value] += 1

        if outflow < 10:
            micro_10_count += 1
            micro_10_amount += outflow
        if outflow < 20:
            micro_20_count += 1
            micro_20_amount += outflow

        category = _normalize_category(row["category"])
        merchant = row["merchant_name"] or row["name"] or "Unknown"
        category_totals[category] += outflow
        merchant_totals[category][merchant] += outflow
        top_merchants[merchant] += outflow
        bucket_totals[_bucket_for_category(category)] += outflow

    daily_spend = [
        {
            "date": date_key,
            "amount": round(amount, 2),
            "count": daily_counts.get(date_key, 0),
        }
        for date_key, amount in sorted(daily_amounts.items())
    ]

    treemap = _build_treemap(category_totals, merchant_totals)
    sankey = _build_sankey(income_total, bucket_totals)
    top_merchants_list = _build_top_merchants(top_merchants)

    totals = InsightTotals(
        income=round(income_total, 2),
        spend=round(spend_total, 2),
        net=round(income_total - spend_total, 2),
    )

    micro = _build_micro_stats(
        spend_total,
        spend_count,
        micro_10_amount,
        micro_10_count,
        micro_20_amount,
        micro_20_count,
    )

    return {
        "range": {"start_date": start_date, "end_date": end_date},
        "totals": totals.__dict__,
        "daily_spend": daily_spend,
        "micro_spend": micro,
        "sankey": sankey,
        "treemap": treemap,
        "top_merchants": top_merchants_list,
    }


def _split_flow(amount: float, account_type: str | None) -> tuple[float, float]:
    # Credit accounts report charges as positive and payments as negative, so invert inflow/outflow.
    is_credit = (account_type or "").lower() == "credit"
    if is_credit:
        if amount >= 0:
            return amount, 0.0
        return 0.0, -amount
    if amount <= 0:
        return -amount, 0.0
    return 0.0, amount


def _normalize_category(value: str | None) -> str:
    if not value:
        return "Uncategorized"
    if "," in value:
        return value.split(",", 1)[0].strip() or "Uncategorized"
    return value


def _bucket_for_category(category: str) -> str:
    lowered = category.lower()
    if lowered in DEBT_CATEGORIES:
        return "Debt"
    if lowered in FIXED_CATEGORIES:
        return "Fixed"
    return "Discretionary"


def _build_treemap(
    category_totals: dict[str, float],
    merchant_totals: dict[str, dict[str, float]],
) -> list[dict]:
    treemap: list[dict] = []
    sorted_categories = sorted(
        category_totals.items(), key=lambda item: item[1], reverse=True
    )
    for category, total in sorted_categories[:12]:
        merchants = merchant_totals.get(category, {})
        sorted_merchants = sorted(
            merchants.items(), key=lambda item: item[1], reverse=True
        )
        children = [
            {"name": name, "value": round(value, 2)}
            for name, value in sorted_merchants[:10]
        ]
        if len(sorted_merchants) > 10:
            other_total = sum(value for _, value in sorted_merchants[10:])
            if other_total > 0:
                children.append({"name": "Other", "value": round(other_total, 2)})
        treemap.append(
            {"name": category, "value": round(total, 2), "children": children}
        )
    return treemap


def _build_sankey(income_total: float, bucket_totals: dict[str, float]) -> dict:
    nodes = [
        {"name": "Income"},
        {"name": "Fixed"},
        {"name": "Debt"},
        {"name": "Discretionary"},
    ]
    links: list[dict] = []
    for bucket in ("Fixed", "Debt", "Discretionary"):
        value = round(bucket_totals.get(bucket, 0.0), 2)
        if value > 0:
            links.append({"source": "Income", "target": bucket, "value": value})
    if not links and income_total > 0:
        links.append(
            {
                "source": "Income",
                "target": "Discretionary",
                "value": round(income_total, 2),
            }
        )
    return {"nodes": nodes, "links": links}


def _build_top_merchants(merchant_totals: dict[str, float]) -> list[dict]:
    entries = sorted(merchant_totals.items(), key=lambda item: item[1], reverse=True)
    return [{"name": name, "amount": round(amount, 2)} for name, amount in entries[:8]]


def _build_micro_stats(
    spend_total: float,
    spend_count: int,
    micro_10_amount: float,
    micro_10_count: int,
    micro_20_amount: float,
    micro_20_count: int,
) -> dict:
    total_amount = spend_total or 0.0
    total_count = spend_count or 0
    return {
        "total": {"amount": round(total_amount, 2), "count": total_count},
        "lt_10": {
            "amount": round(micro_10_amount, 2),
            "count": micro_10_count,
            "share_amount": (
                round((micro_10_amount / total_amount) * 100, 2)
                if total_amount
                else 0.0
            ),
            "share_count": (
                round((micro_10_count / total_count) * 100, 2) if total_count else 0.0
            ),
        },
        "lt_20": {
            "amount": round(micro_20_amount, 2),
            "count": micro_20_count,
            "share_amount": (
                round((micro_20_amount / total_amount) * 100, 2)
                if total_amount
                else 0.0
            ),
            "share_count": (
                round((micro_20_count / total_count) * 100, 2) if total_count else 0.0
            ),
        },
    }
