from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from .config import Config


@dataclass(frozen=True)
class TellerAuth:
    token: str
    cert_path: str
    key_path: str


def build_teller_auth(config: Config) -> TellerAuth:
    if not config.teller_token:
        raise ValueError("TELLER_TOKEN is required")
    if not config.teller_cert_path or not config.teller_key_path:
        raise ValueError("TELLER_CERT_PATH and TELLER_KEY_PATH are required")
    cert_path = Path(config.teller_cert_path)
    key_path = Path(config.teller_key_path)
    if not cert_path.exists():
        raise ValueError(f"TELLER_CERT_PATH not found: {cert_path}")
    if not key_path.exists():
        raise ValueError(f"TELLER_KEY_PATH not found: {key_path}")
    return TellerAuth(
        token=config.teller_token,
        cert_path=str(cert_path),
        key_path=str(key_path),
    )


class TellerClient:
    def __init__(self, config: Config) -> None:
        self._base_url = config.teller_api_base.rstrip("/")
        auth = build_teller_auth(config)
        self._auth = HTTPBasicAuth(auth.token, "")
        self._cert = (auth.cert_path, auth.key_path)
        self._session = requests.Session()

    def list_accounts(self) -> list[dict[str, Any]]:
        # Context7 (teller_io) snippet:
        # curl https://api.teller.io/accounts -u ACCESS_TOKEN:
        response = self._session.get(
            f"{self._base_url}/accounts",
            auth=self._auth,
            cert=self._cert,
            timeout=30,
        )
        return _parse_json(response)

    def get_balances(self, account_id: str) -> dict[str, Any]:
        # Context7 (teller_io) snippet:
        # curl https://api.teller.io/accounts/:account_id/balances -u ACCESS_TOKEN:
        response = self._session.get(
            f"{self._base_url}/accounts/{account_id}/balances",
            auth=self._auth,
            cert=self._cert,
            timeout=30,
        )
        return _parse_json(response)

    def list_transactions(
        self,
        account_id: str,
        count: int | None = None,
        from_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        # Context7 (teller_io) snippet:
        # GET /accounts/:account_id/transactions
        # Pagination parameters: count, from_id, start_date, end_date
        # start_date: include only transactions on/after this date (YYYY-MM-DD).
        # end_date: include only transactions on/before this date (YYYY-MM-DD).
        params: dict[str, Any] = {}
        if count is not None:
            params["count"] = count
        if from_id:
            params["from_id"] = from_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        response = self._session.get(
            f"{self._base_url}/accounts/{account_id}/transactions",
            auth=self._auth,
            cert=self._cert,
            params=params,
            timeout=30,
        )
        return _parse_json(response)


class TellerApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, retry_after: str | None) -> None:
        super().__init__(f"{status_code} {message}")
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after


def _parse_json(response: requests.Response) -> Any:
    if response.status_code >= 400:
        raise TellerApiError(
            response.status_code,
            response.text.strip(),
            response.headers.get("Retry-After"),
        )
    return response.json()
