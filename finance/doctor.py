import logging
from pathlib import Path

from . import db
from .config import Config
from .teller_client import TellerClient, build_teller_auth

logger = logging.getLogger(__name__)


class DoctorResult:
    def __init__(self) -> None:
        self.ok = True
        self.messages: list[str] = []

    def add(self, ok: bool, message: str) -> None:
        if not ok:
            self.ok = False
        self.messages.append(f"{'OK' if ok else 'FAIL'} {message}")


def run_doctor(config: Config) -> int:
    result = DoctorResult()

    _check_env(config, result)

    try:
        conn = db.connect(config.db_path)
        db.init_db(conn)
        result.add(True, f"db ok ({config.db_path})")
    except Exception as exc:
        result.add(False, f"db init failed: {exc}")
        return _print_and_exit(result)

    if not result.ok:
        return _print_and_exit(result)

    try:
        client = TellerClient(config)
        accounts = client.list_accounts()
        result.add(True, f"teller ok ({len(accounts)} accounts)")
    except Exception as exc:
        result.add(False, f"teller request failed: {exc}")

    return _print_and_exit(result)


def _check_env(config: Config, result: DoctorResult) -> None:
    result.add(bool(config.teller_token), "TELLER_TOKEN set")

    cert_path = Path(config.teller_cert_path or "")
    key_path = Path(config.teller_key_path or "")
    result.add(bool(config.teller_cert_path), "TELLER_CERT_PATH set")
    result.add(bool(config.teller_key_path), "TELLER_KEY_PATH set")
    if config.teller_cert_path:
        result.add(cert_path.exists(), f"cert exists ({cert_path})")
    if config.teller_key_path:
        result.add(key_path.exists(), f"key exists ({key_path})")

    try:
        build_teller_auth(config)
    except Exception as exc:
        result.add(False, f"teller auth invalid: {exc}")

    if config.llm_enabled:
        result.add(bool(config.openai_api_key), "OPENAI_API_KEY set (LLM enabled)")
        try:
            import openai  # noqa: F401

            result.add(True, "openai package installed")
        except Exception as exc:
            result.add(False, f"openai package missing: {exc}")
    else:
        result.add(True, "LLM disabled (set FINANCE_LLM_ENABLED=true to enable)")


def _print_and_exit(result: DoctorResult) -> int:
    for message in result.messages:
        print(message)
    return 0 if result.ok else 1
