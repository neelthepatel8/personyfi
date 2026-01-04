import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    db_path: str
    teller_api_base: str
    teller_token: str | None
    teller_cert_path: str | None
    teller_key_path: str | None
    api_host: str
    api_port: int
    ingest_interval_minutes: int
    ingest_lookback_days: int
    ingest_page_size: int


def load_config() -> Config:
    db_path = os.getenv("FINANCE_DB_PATH", "finance.db")
    teller_api_base = os.getenv("TELLER_API_BASE", "https://api.teller.io")
    teller_token = os.getenv("TELLER_TOKEN")
    teller_cert_path = _normalize_path(os.getenv("TELLER_CERT_PATH"))
    teller_key_path = _normalize_path(os.getenv("TELLER_KEY_PATH"))
    api_host = os.getenv("FINANCE_API_HOST", "127.0.0.1")
    api_port = _parse_int("FINANCE_API_PORT", 3030)
    ingest_interval_minutes = _parse_int("FINANCE_INGEST_INTERVAL_MINUTES", 10)
    ingest_lookback_days = _parse_int("FINANCE_INGEST_LOOKBACK_DAYS", 10)
    ingest_page_size = _parse_int("FINANCE_INGEST_PAGE_SIZE", 50)

    return Config(
        db_path=db_path,
        teller_api_base=teller_api_base,
        teller_token=teller_token,
        teller_cert_path=teller_cert_path,
        teller_key_path=teller_key_path,
        api_host=api_host,
        api_port=api_port,
        ingest_interval_minutes=ingest_interval_minutes,
        ingest_lookback_days=ingest_lookback_days,
        ingest_page_size=ingest_page_size,
    )


def _normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return str(path)


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
