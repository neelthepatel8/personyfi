import json
import logging
import threading
import time
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db
from .config import Config
from .ingest import ingest_all, ingest_one_account
from .inbox import load_unknown_merchants
from .insights import build_insights
from .llm import categorize_with_llm, LlmError
from . import rules as rules_engine

logger = logging.getLogger(__name__)


class ApiState:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.ingest_lock = threading.Lock()
        self.last_ingest_at: str | None = None
        self.last_ingest_error: str | None = None


class FinanceHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], state: ApiState) -> None:
        super().__init__(server_address, FinanceAPIHandler)
        self.state = state


class FinanceAPIHandler(BaseHTTPRequestHandler):
    server: FinanceHTTPServer

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/ui"):
            self._send_file("index.html", "text/html")
            return
        if path == "/health":
            self._send_json(200, {"ok": True})
            return
        if path == "/accounts":
            self._send_json(200, _list_accounts(self.server.state.config))
            return
        if path == "/transactions":
            try:
                response = _list_transactions(self.server.state.config, query)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, response)
            return
        if path == "/inbox":
            limit = _parse_int(query.get("limit", ["100"])[0], 100, 1000)
            conn = db.connect(self.server.state.config.db_path)
            try:
                entries = load_unknown_merchants(conn)
            finally:
                conn.close()
            self._send_json(200, {"count": len(entries), "items": entries[:limit]})
            return
        if path == "/status":
            self._send_json(200, _status(self.server.state))
            return
        if path == "/rules":
            self._send_json(200, _list_rules(self.server.state.config))
            return
        if path == "/insights":
            try:
                response = _list_insights(self.server.state.config, query)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, response)
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        if path == "/ingest":
            result = _trigger_ingest(self.server.state, payload)
            status = 200 if result.get("ok") else 409
            self._send_json(status, result)
            return
        if path == "/rules":
            try:
                result = _create_rule(self.server.state.config, payload)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, result)
            return
        if path == "/categorize":
            try:
                result = _categorize(self.server.state.config, payload)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, result)
            return

        self._send_json(404, {"error": "not found"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON body") from exc

    def _send_json(self, status: int, payload: object) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, filename: str, content_type: str) -> None:
        base_dir = Path(__file__).resolve().parent / "static"
        target = (base_dir / filename).resolve()
        if not str(target).startswith(str(base_dir)) or not target.exists():
            self._send_json(404, {"error": "not found"})
            return
        data = target.read_bytes()
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def serve_api(
    config: Config,
    host: str | None = None,
    port: int | None = None,
    interval_minutes: int | None = None,
    lookback_days: int | None = None,
    page_size: int | None = None,
    schedule: bool = True,
) -> int:
    state = ApiState(config)
    bind_host = host or config.api_host
    bind_port = port or config.api_port

    conn = db.connect(config.db_path)
    try:
        db.init_db(conn)
    finally:
        conn.close()

    if schedule:
        thread = threading.Thread(
            target=_schedule_loop,
            args=(state, interval_minutes, lookback_days, page_size),
            daemon=True,
        )
        thread.start()

    server = FinanceHTTPServer((bind_host, bind_port), state)
    logger.info("API server listening on %s:%s", bind_host, bind_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def _schedule_loop(
    state: ApiState,
    interval_minutes: int | None,
    lookback_days: int | None,
    page_size: int | None,
) -> None:
    interval = interval_minutes or state.config.ingest_interval_minutes
    delay = max(interval, 1) * 60
    while True:
        _trigger_ingest(
            state,
            {
                "lookback_days": lookback_days,
                "page_size": page_size,
            },
        )
        time.sleep(delay)


def _trigger_ingest(state: ApiState, payload: dict) -> dict:
    if not state.ingest_lock.acquire(blocking=False):
        return {"ok": False, "error": "ingest already running"}

    try:
        account_id = payload.get("account_id")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        page_size = payload.get("page_size")
        lookback_days = payload.get("lookback_days")
        full = bool(payload.get("full"))

        if full:
            start_date = None
            end_date = None
        elif not start_date and not end_date:
            start_date, end_date = _default_window(state.config, lookback_days)

        page_size = page_size or state.config.ingest_page_size

        if account_id:
            ingest_one_account(
                state.config,
                account_id,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
            )
        else:
            ingest_all(
                state.config,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
            )

        state.last_ingest_at = db.utc_now()
        state.last_ingest_error = None
        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "page_size": page_size,
        }
    except Exception as exc:
        state.last_ingest_error = str(exc)
        return {"ok": False, "error": str(exc)}
    finally:
        state.ingest_lock.release()


def _default_window(config: Config, lookback_days: int | None) -> tuple[str, str]:
    days = lookback_days or config.ingest_lookback_days
    days = max(days, 1)
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _list_accounts(config: Config) -> dict:
    conn = db.connect(config.db_path)
    try:
        rows = conn.execute(
            """
            SELECT account_id, name, official_name, type, subtype, mask, item_id
            FROM accounts
            WHERE item_id = ?
            ORDER BY name
            """
            ,
            ("teller",),
        ).fetchall()
    finally:
        conn.close()
    return {"accounts": [dict(row) for row in rows]}


def _list_transactions(config: Config, query: dict) -> dict:
    account_id = _get_query_value(query, "account_id")
    start_date = _get_query_value(query, "start_date")
    end_date = _get_query_value(query, "end_date")
    limit = _parse_int(query.get("limit", ["200"])[0], 200, 10000)
    offset = _parse_int(query.get("offset", ["0"])[0], 0, 1000000)

    sql = [
        "SELECT t.transaction_id, t.account_id, t.name, t.merchant_name, t.amount, t.iso_currency_code,",
        "t.date, t.pending, t.category, a.name AS account_name, a.type AS account_type",
        "FROM transactions t",
        "LEFT JOIN accounts a ON a.account_id = t.account_id",
        "WHERE t.removed = 0 AND t.item_id = ?",
    ]
    params: list[object] = ["teller"]

    if not start_date and not end_date:
        start_date, end_date = _default_window(config, None)
    if account_id:
        sql.append("AND account_id = ?")
        params.append(account_id)
    if start_date:
        _validate_date(start_date)
        sql.append("AND date >= ?")
        params.append(start_date)
    if end_date:
        _validate_date(end_date)
        sql.append("AND date <= ?")
        params.append(end_date)

    sql.append("ORDER BY date DESC, transaction_id DESC")
    sql.append("LIMIT ? OFFSET ?")
    params.extend([limit, offset])

    conn = db.connect(config.db_path)
    try:
        rows = conn.execute(" ".join(sql), params).fetchall()
        count_sql = [
            "SELECT COUNT(*) as total FROM transactions WHERE removed = 0 AND item_id = ?",
        ]
        count_params: list[object] = ["teller"]
        if account_id:
            count_sql.append("AND account_id = ?")
            count_params.append(account_id)
        if start_date:
            count_sql.append("AND date >= ?")
            count_params.append(start_date)
        if end_date:
            count_sql.append("AND date <= ?")
            count_params.append(end_date)
        total = conn.execute(" ".join(count_sql), count_params).fetchone()[0]
    finally:
        conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(row) for row in rows],
    }


def _list_insights(config: Config, query: dict) -> dict:
    account_id = _get_query_value(query, "account_id")
    start_date = _get_query_value(query, "start_date")
    end_date = _get_query_value(query, "end_date")

    if not start_date and not end_date:
        start_date, end_date = _default_window(config, None)
    if start_date:
        _validate_date(start_date)
    if end_date:
        _validate_date(end_date)

    conn = db.connect(config.db_path)
    try:
        return build_insights(conn, start_date, end_date, account_id=account_id)
    finally:
        conn.close()


def _status(state: ApiState) -> dict:
    conn = db.connect(state.config.db_path)
    try:
        rows = conn.execute(
            """
            SELECT a.account_id,
                   a.name,
                   a.type,
                   a.subtype,
                   s.last_transaction_id,
                   s.last_sync_at,
                   COUNT(t.id) as transaction_count
            FROM accounts a
            LEFT JOIN account_sync s ON s.account_id = a.account_id
            LEFT JOIN transactions t ON t.account_id = a.account_id AND t.removed = 0
            WHERE a.item_id = ?
            GROUP BY a.account_id, a.name, a.type, a.subtype, s.last_transaction_id, s.last_sync_at
            ORDER BY a.name
            """
            ,
            ("teller",),
        ).fetchall()
    finally:
        conn.close()

    return {
        "last_ingest_at": state.last_ingest_at,
        "last_ingest_error": state.last_ingest_error,
        "accounts": [dict(row) for row in rows],
    }


def _list_rules(config: Config) -> dict:
    conn = db.connect(config.db_path)
    try:
        rules = rules_engine.list_rules(conn)
    finally:
        conn.close()
    return {
        "rules": [
            {
                "id": rule.id,
                "pattern": rule.pattern,
                "match_type": rule.match_type,
                "category": rule.category,
                "merchant": rule.merchant,
                "priority": rule.priority,
                "active": rule.active,
            }
            for rule in rules
        ]
    }


def _create_rule(config: Config, payload: dict) -> dict:
    pattern = (payload.get("pattern") or "").strip()
    if not pattern:
        raise ValueError("pattern is required")
    match_type = (payload.get("match_type") or "contains").strip().lower()
    if match_type not in ("contains", "regex"):
        raise ValueError("match_type must be contains or regex")
    category = (payload.get("category") or "").strip()
    if not category:
        raise ValueError("category is required")
    merchant = (payload.get("merchant") or "").strip() or None
    priority = _parse_int(str(payload.get("priority") or 100), 100, 1000)

    conn = db.connect(config.db_path)
    try:
        db.init_db(conn)
        rule = rules_engine.create_rule(
            conn, pattern, match_type, category, merchant, priority
        )
    finally:
        conn.close()

    return {
        "rule": {
            "id": rule.id,
            "pattern": rule.pattern,
            "match_type": rule.match_type,
            "category": rule.category,
            "merchant": rule.merchant,
            "priority": rule.priority,
            "active": rule.active,
        }
    }


def _categorize(config: Config, payload: dict) -> dict:
    account_id = payload.get("account_id")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    lookback_days = payload.get("lookback_days")
    if lookback_days is not None:
        lookback_days = _parse_int(str(lookback_days), config.ingest_lookback_days, 3650)
    full = bool(payload.get("full"))
    mode = (payload.get("mode") or "rules").strip().lower()
    limit = payload.get("limit")
    if limit is not None:
        limit = _parse_int(str(limit), 0, 10000)

    if not full:
        if not start_date and not end_date:
            start_date, end_date = _default_window(config, lookback_days)
    else:
        start_date = None
        end_date = None

    if start_date:
        _validate_date(start_date)
    if end_date:
        _validate_date(end_date)

    conn = db.connect(config.db_path)
    llm_result: dict | None = None
    try:
        if mode == "rules":
            rules = rules_engine.list_rules(conn)
            updated = rules_engine.apply_rules_to_transactions(
                conn,
                rules,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            )
        elif mode == "llm":
            llm_result = categorize_with_llm(
                conn,
                config,
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            updated = llm_result["updated"]
        else:
            raise ValueError("mode must be rules or llm")
    except LlmError as exc:
        raise ValueError(str(exc)) from exc
    finally:
        conn.close()

    return {
        "updated": updated,
        "start_date": start_date,
        "end_date": end_date,
        "mode": mode,
        "limit": limit,
        "llm": llm_result,
    }


def _get_query_value(query: dict, name: str) -> str | None:
    values = query.get(name)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _parse_int(raw: str, default: int, maximum: int) -> int:
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("invalid integer") from exc
    return max(0, min(value, maximum))


def _validate_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("dates must be YYYY-MM-DD") from exc
