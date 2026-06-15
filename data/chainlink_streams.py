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


def _is_number(v) -> bool:
    """Numeric int/float — bool REDDEDİLİR (True/False fiyat/scale/timestamp değildir)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def normalize_crypto_v3_report(report, *, price_scale):
    """Zaten-DECODE-edilmiş Crypto v3 report dict'ini sade {feed_id, timestamp_ms, price}'a çevirir.

    fullReport blob DECODE EDİLMEZ; raw REST (fullReport var ama decoded price yok) → ValueError. feed id
    feedID/feedId (non-empty str); observationsTimestamp int saniye (bool red); price price/benchmarkPrice/
    BenchmarkPrice numeric (bool red); price_scale pozitif numeric (bool red). Çıktı YALNIZ
    feed_id/timestamp_ms/price — opak/fullReport/validFromTimestamp TAŞINMAZ. İhlal → ValueError.
    Canlı fetch/secret YOK."""
    if not isinstance(report, dict):
        raise ValueError(f"report dict olmalı, bulundu: {type(report).__name__}")

    feed_id = report.get("feedID", report.get("feedId"))
    if not isinstance(feed_id, str) or not feed_id:
        raise ValueError(f"feed id (feedID/feedId) non-empty str olmalı: {feed_id!r}")

    ts = report.get("observationsTimestamp")
    if not isinstance(ts, int) or isinstance(ts, bool):
        raise ValueError(f"observationsTimestamp int saniye olmalı (bool değil): {ts!r}")

    price = None
    for key in ("price", "benchmarkPrice", "BenchmarkPrice"):
        if key in report:
            price = report[key]
            break
    if not _is_number(price):
        raise ValueError(f"price (price/benchmarkPrice/BenchmarkPrice) numeric olmalı: {price!r}")

    if not _is_number(price_scale) or price_scale <= 0:
        raise ValueError(f"price_scale pozitif numeric olmalı: {price_scale!r}")

    return {
        "feed_id": feed_id,
        "timestamp_ms": ts * 1000,
        "price": price / price_scale,
    }
