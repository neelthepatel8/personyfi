import httpx
import typing
from base64 import b64encode


from dataclasses import dataclass

@dataclass
class TellerInstitution:
    id: str
    name: str

    def __repr__(self):
        return f"<TellerInstitution: {self.name} ({self.id})>"

@dataclass
class TellerAccount:
    id: str
    name: str
    type: str
    subtype: str
    status: str
    last_four: str
    currency: str
    institution: TellerInstitution
    enrollment_id: str
    links: dict

    @classmethod
    def from_dict(cls, data: dict):
        inst_data = data.get("institution", {})
        institution = TellerInstitution(
            id=inst_data.get("id", ""),
            name=inst_data.get("name", "")
        )
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            subtype=data.get("subtype", ""),
            status=data.get("status", ""),
            last_four=data.get("last_four", ""),
            currency=data.get("currency", ""),
            institution=institution,
            enrollment_id=data.get("enrollment_id", ""),
            links=data.get("links", {})
        )

    def __repr__(self):
        return f"<TellerAccount: {self.name} (****{self.last_four}) - {self.institution.name}>"

@dataclass
class TellerTransaction:
    id: str
    account_id: str
    amount: str
    date: str
    description: str
    status: str
    type: str
    details: dict
    running_balance: typing.Optional[str]
    links: dict

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            account_id=data.get("account_id", ""),
            amount=data.get("amount", ""),
            date=data.get("date", ""),
            description=data.get("description", ""),
            status=data.get("status", ""),
            type=data.get("type", ""),
            details=data.get("details", {}),
            running_balance=data.get("running_balance"),
            links=data.get("links", {})
        )

    def __repr__(self):
        return f"<TellerTransaction: {self.date} - {self.description} (${self.amount})>"


class TellerClient:
    """
    A client for the Teller API using httpx.
    """
    
    BASE_URL = "https://api.teller.io"

    def __init__(
        self,
        token: str,
        cert: typing.Optional[typing.Tuple[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize the Teller Client.

        :param token: The Teller application Access Token.
        :param cert: A tuple of (cert_path, key_path) for mutual TLS (required for most envs).
        :param timeout: Request timeout in seconds.
        """
        self.token = token
        self.cert = cert
        self.timeout = timeout
        
        # Pre-calculate the Basic Auth header
        # Teller expects: Basic base64(token + ":")
        auth_str = f"{self.token}:"
        b64_auth = b64encode(auth_str.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {b64_auth}",
            "User-Agent": "TellerPythonClient/0.1"
        }

    @property
    def _client(self) -> httpx.Client:
        """
        Create and return a new httpx Client instance with configured auth and certs.
        """
        return httpx.Client(
            base_url=self.BASE_URL,
            headers=self.headers,
            cert=self.cert,
            timeout=self.timeout
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """
        Internal helper to make requests.
        """
        with self._client as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response

    def get(self, path: str, params: typing.Optional[dict] = None) -> typing.Any:
        """
        Perform a GET request to the Teller API.
        """
        response = self._request("GET", path, params=params)
        return response.json()

    def post(self, path: str, json: typing.Optional[dict] = None) -> typing.Any:
        """
        Perform a POST request to the Teller API.
        """
        response = self._request("POST", path, json=json)
        return response.json()

    def delete(self, path: str) -> bool:
        """
        Perform a DELETE request to the Teller API.
        Returns True if successful (204 No Content is common for deletes).
        """
        with self._client as client:
            response = client.delete(path)
            response.raise_for_status()
            return response.status_code in (200, 204)

    # --- Specific Endpoint Helpers (Examples) ---

    def list_accounts(self) -> typing.List[TellerAccount]:
        """
        List all connected accounts.
        Endpoint: /accounts
        """
        data = self.get("/accounts")
        return [TellerAccount.from_dict(acc) for acc in data]

    def get_account(self, account_id: str) -> TellerAccount:
        """
        Get details of a specific account.
        Endpoint: /accounts/:id
        """
        data = self.get(f"/accounts/{account_id}")
        return TellerAccount.from_dict(data)

    def list_transactions(self, account_id: str, count: int = 50) -> typing.List[TellerTransaction]:
        """
        List transactions for an account.
        Endpoint: /accounts/:id/transactions
        """
        data = self.get(f"/accounts/{account_id}/transactions", params={"count": count})
        return [TellerTransaction.from_dict(tx) for tx in data]
