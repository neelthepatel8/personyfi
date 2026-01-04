#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth


def main() -> int:
    load_dotenv()

    token = os.getenv("TELLER_TOKEN")
    cert_path = _resolve_path(os.getenv("TELLER_CERT_PATH"))
    key_path = _resolve_path(os.getenv("TELLER_KEY_PATH"))
    base_url = os.getenv("TELLER_API_BASE", "https://api.teller.io").rstrip("/")

    if not token or not cert_path or not key_path:
        print("FAIL config: TELLER_TOKEN, TELLER_CERT_PATH, TELLER_KEY_PATH required")
        return 1

    # Context7 (teller_io) snippet:
    # curl --cert /path/to/cert.pem --key /path/to/key.pem https://api.teller.io
    # curl -u ACCESS_TOKEN: https://api.teller.io/accounts
    auth = HTTPBasicAuth(token, "")
    cert = (cert_path, key_path)

    try:
        accounts = _get_json(f"{base_url}/accounts", auth, cert)
    except Exception as exc:
        print(f"FAIL accounts: {exc}")
        return 1

    print("OK teller smoke")
    print(f"accounts: {len(accounts)}")

    if not accounts:
        return 0

    first_account_id = accounts[0].get("id")
    if not first_account_id:
        return 0

    try:
        balances = _get_json(f"{base_url}/accounts/{first_account_id}/balances", auth, cert)
        transactions = _get_json(
            f"{base_url}/accounts/{first_account_id}/transactions",
            auth,
            cert,
        )
    except Exception as exc:
        print(f"FAIL account detail: {exc}")
        return 1

    print(f"first_account_id: {first_account_id}")
    print(f"balances: available={balances.get('available')} ledger={balances.get('ledger')}")
    print(f"transactions: {len(transactions)}")
    return 0


def _get_json(url: str, auth: HTTPBasicAuth, cert: tuple[str, str]) -> object:
    delay = 2
    for attempt in range(5):
        response = requests.get(url, auth=auth, cert=cert, timeout=30)
        if response.status_code < 400:
            return response.json()
        if response.status_code in (429, 503, 504) and attempt < 4:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            time.sleep(retry_after or delay)
            delay *= 2
            continue
        raise RuntimeError(f"{response.status_code} {response.text.strip()}")
    raise RuntimeError("request failed after retries")


def _resolve_path(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return str(path)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


if __name__ == "__main__":
    sys.exit(main())
