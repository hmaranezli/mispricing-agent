"""data/chainlink_streams.py — read-only Chainlink Data Streams boundary/validation layer.

F1b'nin tek hard blocker'ı Chainlink BTC/USD Data Streams verisi (auth-gated). Bu modül THIN bir
sınır/doğrulama katmanıdır: gerçek bir fetch/HMAC/endpoint/secret İÇERMEZ — Streams erişimi ENJEKTE
edilen bir `client` üzerinden yapılır (implicit env/default network client YOK). Payload bu katmanda
NORMALIZE EDİLMEZ (price alanı uydurulmaz); ham report dict'leri olduğu gibi döner.

Gerçek authenticated Streams fetch AYRI, açık secret-backed insan onayı + credentials + stream ID
gerektirir — bu modül onu açmaz.
"""


def fetch_stream_reports(stream_id, start_ms, end_ms, *, client):
    """Enjekte `client` üzerinden [start_ms, end_ms) aralığındaki Stream report'larını döner.

    Validation: stream_id non-empty str; start_ms/end_ms int (bool DEĞİL); start_ms < end_ms;
    client.fetch_reports(...) sonucu list-of-dict olmalı. `client.fetch_reports(stream_id=..., start_ms=...,
    end_ms=...)` TAM BİR KEZ çağrılır. Report listesi DEĞİŞTİRİLMEDEN döner (normalize YOK).
    İhlal → ValueError. Canlı fetch/HMAC/secret YOK (client enjekte)."""
    if not isinstance(stream_id, str) or not stream_id:
        raise ValueError(f"stream_id non-empty str olmalı: {stream_id!r}")
    if not isinstance(start_ms, int) or isinstance(start_ms, bool):
        raise ValueError(f"start_ms int olmalı (bool değil): {start_ms!r}")
    if not isinstance(end_ms, int) or isinstance(end_ms, bool):
        raise ValueError(f"end_ms int olmalı (bool değil): {end_ms!r}")
    if start_ms >= end_ms:
        raise ValueError(f"start_ms ({start_ms}) < end_ms ({end_ms}) olmalı")

    reports = client.fetch_reports(stream_id=stream_id, start_ms=start_ms, end_ms=end_ms)

    if not isinstance(reports, list):
        raise ValueError(f"client.fetch_reports list döndürmeli, bulundu: {type(reports).__name__}")
    for i, r in enumerate(reports):
        if not isinstance(r, dict):
            raise ValueError(f"report[{i}] dict olmalı, bulundu: {type(r).__name__}")

    return reports
