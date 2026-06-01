"""execution/clob_client.py — py-clob-client-v2 singleton. Lazy init, env'den credentials."""
import os
from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.clob_types import ApiCreds

POLY_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137

_client: ClobClient | None = None


def get_client() -> ClobClient:
    """Singleton ClobClient döndür. İlk çağrıda oluşturulur."""
    global _client
    if _client is None:
        raw_key = os.environ["POLY_PRIVATE_KEY"]
        key = raw_key if raw_key.startswith("0x") else "0x" + raw_key
        creds = ApiCreds(
            api_key=os.environ["POLY_API_KEY"],
            api_secret=os.environ["POLY_API_SECRET"],
            api_passphrase=os.environ["POLY_API_PASSPHRASE"],
        )
        # POLY_FUNDER_ADDRESS = Polymarket deposit/proxy wallet (0x2EBe0...)
        # signature_type=3 (POLY_1271) — new API users deposit wallet flow
        # signature_type=0 (EOA) — funder yoksa standart EOA flow
        funder = os.environ.get("POLY_FUNDER_ADDRESS", "").strip()
        if funder:
            _client = ClobClient(
                host=POLY_HOST,
                chain_id=POLYGON_CHAIN_ID,
                key=key,
                creds=creds,
                signature_type=3,
                funder=funder,
            )
        else:
            _client = ClobClient(
                host=POLY_HOST,
                chain_id=POLYGON_CHAIN_ID,
                key=key,
                creds=creds,
            )
    return _client


def reset_client() -> None:
    """Global state'i sıfırla — test yardımcısı."""
    global _client
    _client = None
