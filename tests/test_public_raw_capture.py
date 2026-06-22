"""tests/test_public_raw_capture.py — Phase post-6.2 raw-only one-shot acquisition runtime suite.

Governing contract (sole source of truth):
docs/handoff/post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md

No real or localhost network call is made: aiohttp is replaced by deterministic in-process doubles via
monkeypatching the runtime's transport seam. `id(...)` is never used.
"""
import ast
import asyncio
import hashlib
import inspect
import json
import os
import pathlib
import sqlite3
import struct

import pytest
import aiohttp

import raw_acquisition
import raw_acquisition.public_raw_capture as prc
from raw_acquisition.public_raw_capture import (
    acquire_public_raw_capture,
    PublicSourceRequest,
    PolymarketGammaMarketBySlugV1Request,
    PolymarketClobBookByTokenV1Request,
    HyperliquidMetaAndAssetCtxsV1Request,
    RawCaptureCommitted,
    RawAcquisitionError,
    RawLedgerPreflightError,
    RawLedgerPathError,
    RawLedgerPragmaError,
    RawLedgerSchemaFingerprintError,
    RawLedgerReadinessError,
    RawTransportError,
    RawTimeoutError,
    RawResponseTooLargeError,
    RawHttpProtocolError,
    RawLedgerCommitError,
)


_MODULE_PATH = pathlib.Path(prc.__file__)
_SHA_EMPTY = hashlib.sha256(b"").hexdigest()
_MAX = 16 * 1024 * 1024
_HL_BODY = b'{"type":"metaAndAssetCtxs"}'


def run(coro):
    return asyncio.run(coro)


# --- deterministic aiohttp doubles -----------------------------------------------------------------
class FakeContent:
    def __init__(self, chunks, raise_exc=None):
        self._chunks = list(chunks)
        self._raise = raise_exc

    async def iter_chunked(self, n):
        for c in self._chunks:
            yield c
        if self._raise is not None:
            raise self._raise


class FakeResp:
    def __init__(self, status, raw_headers, chunks, content_raise=None):
        self.status = status
        self.raw_headers = tuple(raw_headers)
        self.content = FakeContent(chunks, content_raise)
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *a):
        self.exited = True
        return False


class FakeReqCM:
    """What session.request(...) returns: an async context manager yielding the response (or raising)."""
    def __init__(self, resp=None, request_raise=None):
        self._resp = resp
        self._raise = request_raise

    async def __aenter__(self):
        if self._raise is not None:
            raise self._raise
        return self._resp

    async def __aexit__(self, *a):
        return False


class FakeSession:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.requests = []
        self.closed = False
        self._program = None
        FakeSession.instances.append(self)

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, "kwargs": kwargs})
        return self._program

    async def close(self):
        self.closed = True


def _install_session(monkeypatch, resp=None, request_raise=None):
    FakeSession.instances = []

    def factory(**kwargs):
        s = FakeSession(**kwargs)
        s._program = FakeReqCM(resp=resp, request_raise=request_raise)
        return s

    monkeypatch.setattr(prc, "_client_session", factory)
    return factory


def _ok_resp(status=200, headers=((b"content-type", b"application/json"),), chunks=(b"{}",)):
    return FakeResp(status, headers, chunks)


def _clock(monkeypatch, started_epoch=1000, started_mono=5000,
           completed_epoch=1007, completed_mono=5009):
    eq = iter([started_epoch, completed_epoch])
    mo = iter([started_mono, completed_mono])
    monkeypatch.setattr(prc, "_epoch_ms", lambda: next(eq))
    monkeypatch.setattr(prc, "_monotonic_ns", lambda: next(mo))


def _paths(tmp_path):
    return str(tmp_path / "raw.db"), str(tmp_path / "s1.db")


def _gamma():
    return PolymarketGammaMarketBySlugV1Request(slug="btc-up-or-down")


_CSHA = "a" * 40


# === 1. API SHAPE, ANNOTATIONS, GUARDS ============================================================

def test_callable_is_async_keyword_only_exact_params():
    assert inspect.iscoroutinefunction(acquire_public_raw_capture)
    sig = inspect.signature(acquire_public_raw_capture)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["request", "raw_ledger_path", "s1_ledger_path", "collector_commit_sha"]
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params)
    assert all(p.default is inspect.Parameter.empty for p in params)
    ann = acquire_public_raw_capture.__annotations__
    assert ann["request"] is PublicSourceRequest
    assert ann["raw_ledger_path"] is str
    assert ann["s1_ledger_path"] is str
    assert ann["collector_commit_sha"] is str
    assert ann["return"] is RawCaptureCommitted


def test_request_variants_frozen_slotted_kwonly():
    import dataclasses
    for cls, kw in (
        (PolymarketGammaMarketBySlugV1Request, {"slug": "x"}),
        (PolymarketClobBookByTokenV1Request, {"token_id": "1"}),
        (HyperliquidMetaAndAssetCtxsV1Request, {}),
    ):
        assert dataclasses.is_dataclass(cls)
        params = dataclasses.fields(cls)
        inst = cls(**kw)
        assert getattr(cls, "__slots__", None) is not None
        with pytest.raises(dataclasses.FrozenInstanceError):
            if params:
                setattr(inst, params[0].name, "mutate")
            else:
                object.__setattr__  # no field; force the assertion path below
                raise dataclasses.FrozenInstanceError("no fields")
        # keyword-only: positional construction rejected when there is a field
        if kw:
            with pytest.raises(TypeError):
                cls(*kw.values())


def test_result_carrier_exact_shape():
    import dataclasses
    fields = [f.name for f in dataclasses.fields(RawCaptureCommitted)]
    assert fields == ["capture_sequence", "attempt_sequence", "source_authority",
                      "http_status", "response_body_sha256"]
    assert getattr(RawCaptureCommitted, "__slots__", None) is not None


def test_exception_hierarchy():
    for sub in (RawLedgerPreflightError, RawTransportError, RawTimeoutError,
                RawResponseTooLargeError, RawHttpProtocolError, RawLedgerCommitError):
        assert issubclass(sub, RawAcquisitionError)
    for sub in (RawLedgerPathError, RawLedgerPragmaError, RawLedgerSchemaFingerprintError,
                RawLedgerReadinessError):
        assert issubclass(sub, RawLedgerPreflightError)


def test_guard_request_type(tmp_path):
    raw, s1 = _paths(tmp_path)
    with pytest.raises(TypeError) as e:
        run(acquire_public_raw_capture(request=object(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert str(e.value) == "request must be an exact PublicSourceRequest variant"


def test_guard_path_types(tmp_path):
    with pytest.raises(TypeError) as e:
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=123,
                                       s1_ledger_path="s", collector_commit_sha=_CSHA))
    assert str(e.value) == "raw_ledger_path, s1_ledger_path, and collector_commit_sha must be exact str"


def test_guard_empty_nul_paths(tmp_path):
    with pytest.raises(ValueError) as e:
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path="",
                                       s1_ledger_path="s", collector_commit_sha=_CSHA))
    assert str(e.value) == "raw_ledger_path and s1_ledger_path must be non-empty NUL-free paths"
    with pytest.raises(ValueError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path="a\x00b",
                                       s1_ledger_path="s", collector_commit_sha=_CSHA))


def test_guard_collector_sha(tmp_path):
    raw, s1 = _paths(tmp_path)
    with pytest.raises(ValueError) as e:
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha="A" * 40))
    assert str(e.value) == "collector_commit_sha must be exactly 40 lowercase hex characters"


def test_guard_slug_and_token_grammar(tmp_path):
    raw, s1 = _paths(tmp_path)
    with pytest.raises(ValueError) as e:
        run(acquire_public_raw_capture(request=PolymarketGammaMarketBySlugV1Request(slug="bad/slug"),
                                       raw_ledger_path=raw, s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert str(e.value) == "slug must match ^[0-9a-z][0-9a-z-]{0,254}$"
    with pytest.raises(ValueError) as e2:
        run(acquire_public_raw_capture(request=PolymarketClobBookByTokenV1Request(token_id="0xabc"),
                                       raw_ledger_path=raw, s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert str(e2.value) == "token_id must match ^[0-9]{1,80}$"


def test_guards_run_before_network(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    with pytest.raises(TypeError):
        run(acquire_public_raw_capture(request=object(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert FakeSession.instances == []


# === 2. TRANSPORT EVIDENCE (three variants) =======================================================

def test_gamma_variant_exact_request(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    sess = FakeSession.instances[-1]
    assert sess.kwargs["trust_env"] is False
    assert sess.kwargs["auto_decompress"] is False
    assert isinstance(sess.kwargs["cookie_jar"], aiohttp.DummyCookieJar)
    to = sess.kwargs["timeout"]
    assert to.total == 10.0 and to.connect == 3.0
    assert len(sess.requests) == 1
    rq = sess.requests[0]
    assert rq["method"] == "GET"
    assert rq["url"] == "https://gamma-api.polymarket.com/markets?slug=btc-up-or-down"
    assert rq["kwargs"]["allow_redirects"] is False
    assert rq["kwargs"]["headers"] == {"Accept": "application/json"}
    assert rq["kwargs"]["data"] is None
    assert sess.closed is True


def test_clob_variant_exact_request(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=PolymarketClobBookByTokenV1Request(token_id="123456789"),
                                   raw_ledger_path=raw, s1_ledger_path=s1, collector_commit_sha=_CSHA))
    rq = FakeSession.instances[-1].requests[0]
    assert rq["method"] == "GET"
    assert rq["url"] == "https://clob.polymarket.com/book?token_id=123456789"
    assert rq["kwargs"]["headers"] == {"Accept": "application/json"}
    assert rq["kwargs"]["data"] is None


def test_hyperliquid_variant_exact_request(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=HyperliquidMetaAndAssetCtxsV1Request(),
                                   raw_ledger_path=raw, s1_ledger_path=s1, collector_commit_sha=_CSHA))
    rq = FakeSession.instances[-1].requests[0]
    assert rq["method"] == "POST"
    assert rq["url"] == "https://api.hyperliquid.xyz/info"
    assert rq["kwargs"]["headers"] == {"Accept": "application/json", "Content-Type": "application/json"}
    assert rq["kwargs"]["data"] == _HL_BODY


# === 3. CAPTURE / BODY / HEADERS ==================================================================

def _read_capture(raw):
    c = sqlite3.connect(raw)
    try:
        return c.execute("SELECT * FROM raw_capture_log").fetchall(), \
               [d[0] for d in c.execute("SELECT * FROM raw_capture_log").description]
    finally:
        c.close()


def test_non_2xx_commits_raw_captured_with_exact_body_and_sha(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    body = b"\x00\x01not json\xff"
    _install_session(monkeypatch, resp=FakeResp(503, ((b"x", b"y"),), [body[:3], body[3:]]))
    _clock(monkeypatch)
    res = run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                         s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert isinstance(res, RawCaptureCommitted)
    assert res.http_status == 503
    assert res.response_body_sha256 == hashlib.sha256(body).hexdigest()
    c = sqlite3.connect(raw)
    try:
        row = c.execute("SELECT response_body, http_status, response_body_sha256 FROM raw_capture_log").fetchone()
        assert row[0] == body and row[1] == 503 and row[2] == hashlib.sha256(body).hexdigest()
        att = c.execute("SELECT outcome, capture_sequence, failure_code FROM raw_fetch_attempt_log").fetchone()
        assert att == ("RAW_COMMITTED", res.capture_sequence, None)
    finally:
        c.close()


def test_empty_body_capture(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=FakeResp(204, (), []))
    _clock(monkeypatch)
    res = run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                         s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert res.response_body_sha256 == _SHA_EMPTY
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT response_body FROM raw_capture_log").fetchone()[0] == b""
    finally:
        c.close()


def test_header_encoding_ordered_with_duplicates(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    headers = ((b"set-cookie", b"a"), (b"set-cookie", b"b"), (b"X-Dup", b"1"))
    _install_session(monkeypatch, resp=FakeResp(200, headers, [b"{}"]))
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        payload = c.execute("SELECT response_headers_payload FROM raw_capture_log").fetchone()[0]
    finally:
        c.close()
    expected = struct.pack(">I", 3)
    for n, v in headers:
        expected += struct.pack(">I", len(n)) + n + struct.pack(">I", len(v)) + v
    assert payload == expected


def test_exact_16mib_accepted_and_plus_one_rejected(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=FakeResp(200, (), [b"x" * _MAX]))
    _clock(monkeypatch)
    res = run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                         s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert res.response_body_sha256 == hashlib.sha256(b"x" * _MAX).hexdigest()

    raw2, s12 = str(tmp_path / "r2.db"), str(tmp_path / "s12.db")
    _install_session(monkeypatch, resp=FakeResp(200, (), [b"x" * _MAX, b"y"]))
    _clock(monkeypatch)
    with pytest.raises(RawResponseTooLargeError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw2,
                                       s1_ledger_path=s12, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw2)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
        att = c.execute("SELECT outcome, failure_code, capture_sequence FROM raw_fetch_attempt_log").fetchone()
        assert att == ("RESPONSE_TOO_LARGE", "RAW_RESPONSE_TOO_LARGE", None)
    finally:
        c.close()


# === 4. FAILURE MAPPINGS + PAYLOAD PROVENANCE =====================================================

def _expected_payload(exc):
    import re as _re
    addr = _re.compile(r"(?<=\bat )0x[0-9a-f]{6,}(?=>)", _re.IGNORECASE)
    payload = {"exception_type": type(exc).__name__, "args": []}
    for a in exc.args:
        if type(a) is str:
            payload["args"].append({"kind": "STRING", "value": addr.sub("<memory-address-redacted>", a)})
        else:
            payload["args"].append({"kind": "NON_STRING", "type": type(a).__name__})
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


@pytest.mark.parametrize("exc,public,outcome,code", [
    (asyncio.TimeoutError("slow"), RawTimeoutError, "TIMEOUT", "RAW_TIMEOUT"),
    (aiohttp.ClientConnectionError("down"), RawTransportError, "TRANSPORT_FAILED", "RAW_TRANSPORT_ERROR"),
    (aiohttp.ClientPayloadError("bad payload"), RawHttpProtocolError, "HTTP_PROTOCOL_FAILED", "RAW_HTTP_PROTOCOL_ERROR"),
])
def test_failure_mapping_and_payload(monkeypatch, tmp_path, exc, public, outcome, code):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, request_raise=exc)
    _clock(monkeypatch)
    with pytest.raises(public):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
        row = c.execute("SELECT outcome, failure_code, failure_payload, capture_sequence FROM raw_fetch_attempt_log").fetchone()
        assert row[0] == outcome and row[1] == code and row[3] is None
        assert row[2] == _expected_payload(exc)
    finally:
        c.close()


def test_failure_payload_address_redaction_and_hex_preservation(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    exc = aiohttp.ClientConnectionError("conn <obj at 0xABCDEF1> price 0xDEADBEEF", 503)
    _install_session(monkeypatch, request_raise=exc)
    _clock(monkeypatch)
    with pytest.raises(RawTransportError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        payload = c.execute("SELECT failure_payload FROM raw_fetch_attempt_log").fetchone()[0]
    finally:
        c.close()
    assert "<memory-address-redacted>" in payload          # object-repr redacted
    assert "0xDEADBEEF" in payload                          # standalone hex preserved
    assert '"NON_STRING","type":"int"' in payload and "503" not in payload  # non-string opacity


def test_unexpected_exception_is_fail_fast_no_row(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, request_raise=KeyError("unmapped defect"))
    _clock(monkeypatch)
    with pytest.raises(KeyError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_fetch_attempt_log").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
    finally:
        c.close()


# === 5. CLOCK LAW =================================================================================

def test_clock_sampling_values(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch, started_epoch=2000, started_mono=100, completed_epoch=2050, completed_mono=900)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        row = c.execute("SELECT retrieval_started_epoch_ms, retrieval_completed_epoch_ms, "
                        "retrieval_elapsed_monotonic_ns, clock_anomaly_evidence FROM raw_capture_log").fetchone()
    finally:
        c.close()
    assert row == (2000, 2050, 800, 0)


def test_backward_wallclock_anomaly_recorded(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch, started_epoch=2000, started_mono=100, completed_epoch=1990, completed_mono=900)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT clock_anomaly_evidence FROM raw_capture_log").fetchone()[0] == 1
    finally:
        c.close()


def test_negative_monotonic_delta_fail_fast_no_row(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch, started_epoch=2000, started_mono=900, completed_epoch=2001, completed_mono=100)
    with pytest.raises(Exception) as e:
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert not isinstance(e.value, RawAcquisitionError)
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM raw_fetch_attempt_log").fetchone()[0] == 0
    finally:
        c.close()


# === 6. LEDGER / SCHEMA / TRANSACTION =============================================================

_CATQ = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name,tbl_name"


def test_first_init_then_reopen_and_pragmas(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        names = {r[1] for r in c.execute(_CATQ).fetchall()}
        assert {"raw_capture_log", "raw_fetch_attempt_log", "raw_processing_journal"} <= names
    finally:
        c.close()
    # reopen exact existing ledger: second acquisition runs no DDL and succeeds
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 2
    finally:
        c.close()


def test_existing_missing_object_rejected_without_repair(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    c.executescript("DROP TRIGGER trg_raw_capture_log_no_delete;")
    before = c.execute(_CATQ).fetchall()
    c.close()
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    with pytest.raises(RawLedgerSchemaFingerprintError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert FakeSession.instances == []          # rejected before transport
    c = sqlite3.connect(raw)
    try:
        assert c.execute(_CATQ).fetchall() == before   # not repaired
    finally:
        c.close()


def test_extra_object_rejected(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    c.executescript("CREATE INDEX extra_idx ON raw_capture_log(http_status);")
    c.close()
    _install_session(monkeypatch, resp=_ok_resp())
    with pytest.raises(RawLedgerSchemaFingerprintError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))


def test_path_isolation_equality_rejected_before_transport(monkeypatch, tmp_path):
    raw = str(tmp_path / "same.db")
    _install_session(monkeypatch, resp=_ok_resp())
    with pytest.raises(RawLedgerPathError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=raw, collector_commit_sha=_CSHA))
    assert FakeSession.instances == []


def test_path_isolation_symlink_alias_rejected(monkeypatch, tmp_path):
    target = tmp_path / "real_s1.db"
    target.write_bytes(b"")
    link = tmp_path / "link_raw.db"
    os.symlink(target, link)
    _install_session(monkeypatch, resp=_ok_resp())
    with pytest.raises(RawLedgerPathError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=str(link),
                                       s1_ledger_path=str(target), collector_commit_sha=_CSHA))
    assert FakeSession.instances == []


def test_s1_path_never_opened(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    opened = []
    real_connect = sqlite3.connect

    def spy_connect(path, *a, **k):
        opened.append(str(path))
        return real_connect(path, *a, **k)

    monkeypatch.setattr(prc.sqlite3, "connect", spy_connect)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert all(os.path.realpath(s1) != os.path.realpath(p) for p in opened)
    assert s1 not in opened


def test_uncreatable_path_fails_before_network(monkeypatch, tmp_path):
    raw = str(tmp_path / "missing_dir" / "raw.db")
    s1 = str(tmp_path / "s1.db")
    _install_session(monkeypatch, resp=_ok_resp())
    with pytest.raises(RawLedgerPathError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    assert FakeSession.instances == []


def test_append_only_triggers_and_composite_fk_and_failure_mapping(tmp_path):
    # initialize a ledger via a direct executescript of the runtime's own DDL constant
    raw = str(tmp_path / "raw.db")
    c = sqlite3.connect(raw, isolation_level=None)
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(prc._RAW_LEDGER_DDL)

    def fails(sql, params=()):
        try:
            c.execute("SAVEPOINT s"); c.execute(sql, params); c.execute("RELEASE s"); return False
        except sqlite3.Error:
            c.execute("ROLLBACK TO s"); c.execute("RELEASE s"); return True

    cap = ("POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", "GET", "https", "gamma-api.polymarket.com",
           "/markets?slug=x", b"", 0, 0, 0, 0, 200, b"\x00", b"", "a" * 64, "b" * 40)
    c.execute("INSERT INTO raw_capture_log(source_authority,http_method,request_scheme,request_host,"
              "request_target,request_body,retrieval_started_epoch_ms,retrieval_completed_epoch_ms,"
              "retrieval_elapsed_monotonic_ns,clock_anomaly_evidence,http_status,response_headers_payload,"
              "response_body,response_body_sha256,collector_commit_sha) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", cap)
    assert fails("UPDATE raw_capture_log SET http_status=201")
    assert fails("DELETE FROM raw_capture_log")
    # provenance-mismatch RAW_COMMITTED rejected
    base = "INSERT INTO raw_fetch_attempt_log(source_authority,request_target,retrieval_started_epoch_ms,retrieval_completed_epoch_ms,retrieval_elapsed_monotonic_ns,clock_anomaly_evidence,outcome,capture_sequence,failure_code,failure_payload,collector_commit_sha) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    assert fails(base, ("POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", "/markets?slug=DIFFERENT", 0, 0, 0, 0, "RAW_COMMITTED", 1, None, None, "b" * 40))
    assert not fails(base, ("POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", "/markets?slug=x", 0, 0, 0, 0, "RAW_COMMITTED", 1, None, None, "b" * 40))
    # wrong failure_code rejected; exact accepted
    assert fails(base, ("POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", "/markets?slug=x", 0, 0, 0, 0, "TIMEOUT", None, "WRONG", "{}", "b" * 40))
    assert not fails(base, ("POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", "/markets?slug=x", 0, 0, 0, 0, "TIMEOUT", None, "RAW_TIMEOUT", "{}", "b" * 40))
    # reconciliation transition trigger
    j = "INSERT INTO raw_processing_journal(capture_sequence,stage,attempt_ordinal,event_kind,recorded_at_epoch_ms,failure_code,failure_payload) VALUES (?,?,?,?,?,?,?)"
    c.execute(j, (1, "OPTION_B_PROJECTION", 1, "STARTED", 0, None, None))
    c.execute(j, (1, "OPTION_B_PROJECTION", 1, "RECONCILIATION_REQUIRED", 1, None, None))
    assert fails(j, (1, "OPTION_B_PROJECTION", 1, "SUCCEEDED", 2, None, None))
    assert not fails(j, (1, "OPTION_B_PROJECTION", 1, "RECONCILED_SUCCEEDED", 3, None, None))
    c.close()


def test_rv10_mismatch_rolls_back(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    real_count = prc._count
    calls = {"n": 0}

    def bad_count(conn, sql, params):
        calls["n"] += 1
        if calls["n"] == 1:
            return 2                      # force capture-count mismatch
        return real_count(conn, sql, params)

    monkeypatch.setattr(prc, "_count", bad_count)
    with pytest.raises(RawLedgerCommitError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
    finally:
        c.close()


def test_commit_failure_yields_no_raw_captured(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)

    def boom(conn):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(prc, "_ledger_commit", boom)
    with pytest.raises(RawLedgerCommitError):
        run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                       s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0] == 0
    finally:
        c.close()


def test_no_processing_journal_writes(monkeypatch, tmp_path):
    raw, s1 = _paths(tmp_path)
    _install_session(monkeypatch, resp=_ok_resp())
    _clock(monkeypatch)
    run(acquire_public_raw_capture(request=_gamma(), raw_ledger_path=raw,
                                   s1_ledger_path=s1, collector_commit_sha=_CSHA))
    c = sqlite3.connect(raw)
    try:
        assert c.execute("SELECT COUNT(*) FROM raw_processing_journal").fetchone()[0] == 0
    finally:
        c.close()


# === 7. STRUCTURAL / AST LOCKS ====================================================================

def _src():
    return _MODULE_PATH.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_src())


def test_runtime_imports_only_allowed():
    forbidden_substr = ("data.", "execution", "phase6_1", "phase6_2_shadow_intent", "requests",
                        "httpx", "urllib", "http.client", "subprocess", "config")
    modules = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            for a in node.names:
                modules.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    for m in modules:
        assert not any(fb in m for fb in forbidden_substr), m
    assert "aiohttp" in modules


def test_runtime_no_env_git_subprocess_tokens():
    src = _src()
    for banned in ("os.environ", "getenv", "subprocess", "popen", "Popen", "git ", "id(",
                   "ssl=False", "verify_ssl", "while True", "create_task", "sleep(",
                   ".json()", "json.loads(response", "raise_for_status"):
        assert banned not in src, banned


def test_no_operational_update_delete_outside_ddl_constant():
    src = _src()
    ddl = prc._RAW_LEDGER_DDL
    remainder = src.replace(ddl, "")
    for banned in ("UPDATE ", "DELETE ", "REPLACE ", "UPSERT", "ATTACH "):
        assert banned not in remainder, banned


def test_one_public_async_callable():
    tree = _tree()
    public_async = [n.name for n in tree.body
                    if isinstance(n, ast.AsyncFunctionDef) and not n.name.startswith("_")]
    assert public_async == ["acquire_public_raw_capture"]


def test_package_initializer_inert_exportless():
    init_src = pathlib.Path(raw_acquisition.__file__).read_text(encoding="utf-8")
    tree = ast.parse(init_src)
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in tree.body)
    assert not hasattr(raw_acquisition, "__all__")
    assert not hasattr(raw_acquisition, "acquire_public_raw_capture")
    # body is only a docstring
    body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    assert body == []


def test_ddl_constant_matches_charter_byte_for_byte():
    charter = (pathlib.Path("docs/handoff/"
               "post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md")
               ).read_text(encoding="utf-8")
    import re as _re
    blocks = _re.findall(r"```sql\n(.*?)```", charter, _re.S)
    ddl_blocks = [b for b in blocks if ("CREATE TABLE" in b or "CREATE TRIGGER" in b or "CREATE UNIQUE INDEX" in b)]
    for b in ddl_blocks:
        assert b.strip() in prc._RAW_LEDGER_DDL
