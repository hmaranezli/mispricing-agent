"""execution/clob_client.py — py-clob-client singleton. Lazy init, env'den credentials."""
import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

POLY_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137

_client: ClobClient | None = None


def get_client() -> ClobClient:
    """Singleton ClobClient döndür. İlk çağrıda oluşturulur."""
    global _client
    if _client is None:
        raw_key = os.environ["POLY_PRIVATE_KEY"]
        key = raw_key if raw_key.startswith("0x") else "0x" + raw_key
        _client = ClobClient(
            host=POLY_HOST,
            key=key,
            chain_id=POLYGON_CHAIN_ID,
            creds=ApiCreds(
                api_key=os.environ["POLY_API_KEY"],
                api_secret=os.environ["POLY_API_SECRET"],
                api_passphrase=os.environ["POLY_API_PASSPHRASE"],
            ),
        )
    return _client


def reset_client() -> None:
    """Global state'i sıfırla — test yardımcısı."""
    global _client
    _client = None
