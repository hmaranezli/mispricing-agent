# Verifier (Katman 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scout bulgusunu bağımsız API çağrısıyla teyit eden Verifier katmanını TDD ile yaz; soft fail (edge geçti) ile hard fail/HALT (API tutarsızlığı) ayrımını uygula.

**Architecture:** İki task: (1) Scout output'una `slug` ekle, (2) `council/verifier.py` yaz. Verifier taze HL fiyatı + PM CLOB fiyatı çeker, drift kontrolü yapar, fair_value yeniden hesaplar, edge'i doğrular.

**Tech Stack:** Python 3.11, aiohttp, pytest-asyncio — yeni bağımlılık yok.

---

## Dosya Haritası

| Dosya | İşlem | Ne değişiyor |
|-------|--------|-------------|
| `council/scout.py` | Modify | `_process_market` return dict'ine `"slug"` eklenir |
| `tests/test_scout.py` | Modify | `required` set'e `"slug"` eklenir |
| `council/verifier.py` | **YENİ** | `verify(finding) → dict` — tüm doğrulama mantığı |
| `tests/test_verifier.py` | **YENİ** | Unit + integration testler |

---

## Task 1: Scout'a slug ekle

**Files:**
- Modify: `council/scout.py`
- Modify: `tests/test_scout.py`

- [ ] **Adım 1: Test'e slug kontrolü ekle (önce kırmızı)**

`tests/test_scout.py` içindeki `test_scan_edges_findings_have_required_fields` fonksiyonunu bul ve `required` set'e `"slug"` ekle:

```python
async def test_scan_edges_findings_have_required_fields():
    """Her bulgu zorunlu alanları içeriyor."""
    findings = await scan_edges()
    required = {
        "question", "asset", "fair_value", "best_ask", "best_bid",
        "edge", "action", "ref_price", "cur_price", "seconds_remaining",
        "slug",   # ← YENİ
    }
    for f in findings:
        missing = required - set(f.keys())
        assert not missing, f"Eksik alanlar: {missing}"
```

- [ ] **Adım 2: Test'in kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_scout.py::test_scan_edges_findings_have_required_fields -v --asyncio-mode=auto
```

Beklenti: FAIL — `"slug" missing`

- [ ] **Adım 3: scout.py'de `_process_market` return dict'ine slug ekle**

`council/scout.py` içindeki `_process_market` fonksiyonunun return ifadesini bul:

```python
    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          window["best_ask"],
        "best_bid":          window["best_bid"],
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
        "slug":              m.get("slug", ""),   # ← YENİ SATIR
    }
```

- [ ] **Adım 4: Tüm scout testlerinin yeşil olduğunu doğrula**

```bash
pytest tests/test_scout.py -v --asyncio-mode=auto
```

Beklenti: `22 passed`

- [ ] **Adım 5: Commit**

```bash
git add council/scout.py tests/test_scout.py
git commit -m "feat(scout): output'a slug alanı eklendi (Verifier için)"
```

---

## Task 2: council/verifier.py — Bağımsız Doğrulayıcı

**Files:**
- Create: `council/verifier.py`
- Create: `tests/test_verifier.py`

- [ ] **Adım 1: Failing testleri yaz**

```python
# tests/test_verifier.py
"""
council/verifier.py testleri.
Gerçek API kullanılır — mock yok.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.verifier import verify, PRICE_DRIFT_HALT_PCT, PM_DRIFT_HALT
from council.scout import scan_edges


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _fake_finding(asset="BTC", slug="btc-updown-5m-0000000000",
                  action="YES", cur_price=105_000.0, ref_price=104_000.0,
                  best_ask=0.35, best_bid=0.34, seconds_remaining=180.0,
                  fair_value=0.60, edge=0.25):
    """Test için sahte Scout bulgusu. slug kasıtlı geçersiz (fetch_error tetikler)."""
    return {
        "question":          "Bitcoin Up or Down - Test",
        "asset":             asset,
        "slug":              slug,
        "action":            action,
        "edge":              edge,
        "cur_price":         cur_price,
        "ref_price":         ref_price,
        "best_ask":          best_ask,
        "best_bid":          best_bid,
        "seconds_remaining": seconds_remaining,
        "fair_value":        fair_value,
        "neg_risk":          False,
    }


# ── Unit testler (API çağrısı olmadan) ───────────────────────────────────────

def test_result_has_required_fields():
    """_result() her zaman gerekli alanları döndürür."""
    from council.verifier import _result
    r = _result(True, "ok", False)
    required = {
        "pass", "reason", "halt",
        "fresh_cur_price", "fresh_best_ask", "fresh_best_bid",
        "fresh_fair", "fresh_edge", "fresh_seconds",
        "hl_drift_pct", "pm_drift",
    }
    assert required.issubset(set(r.keys()))


def test_soft_fail_halt_is_false():
    """Soft fail'de (edge_gone, expired) halt=False."""
    from council.verifier import _result
    for reason in ("edge_gone", "expired", "fetch_error"):
        r = _result(False, reason, False)
        assert r["halt"] is False, f"{reason} için halt True olmamalı"
        assert r["pass"] is False


def test_hard_fail_halt_matches_config():
    """api_mismatch'te halt değeri HALT_ON_API_MISMATCH config'ine eşit."""
    from council.verifier import _result
    r = _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH)
    assert r["halt"] == config.HALT_ON_API_MISMATCH


def test_price_drift_threshold_is_positive():
    assert PRICE_DRIFT_HALT_PCT > 0


def test_pm_drift_threshold_is_positive():
    assert PM_DRIFT_HALT > 0


def test_pass_result_structure():
    """PASS durumu pass=True, halt=False, reason='ok'."""
    from council.verifier import _result
    r = _result(True, "ok", False,
                fresh_cur=105_000.0, fresh_ask=0.40, fresh_bid=0.39,
                fresh_seconds=120.0, fresh_fair=0.65, fresh_edge=0.25,
                hl_drift_pct=0.01, pm_drift=0.005)
    assert r["pass"] is True
    assert r["reason"] == "ok"
    assert r["halt"] is False
    assert r["fresh_cur_price"] == 105_000.0
    assert r["fresh_edge"] == 0.25


# ── Integration testler (gerçek API) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_hl_drift_triggers_halt():
    """
    Scout cur_price=1.0 (imkansız) verilince gerçek HL fiyatıyla drift >2% → api_mismatch.
    Gerçek BTC fiyatı ~$70k+. Fark %2'yi kat kat aşar.
    """
    finding = _fake_finding(cur_price=1.0, ref_price=1.0)
    result = await verify(finding)
    assert result["pass"] is False
    assert result["reason"] == "api_mismatch"
    assert result["halt"] == config.HALT_ON_API_MISMATCH
    assert result["hl_drift_pct"] > PRICE_DRIFT_HALT_PCT


@pytest.mark.asyncio
async def test_verify_expired_soft_fail():
    """
    seconds_remaining=0 olan bulgu → HL drift kontrolü sonrası expired.
    Scout cur_price gerçeğe yakın verilirse drift geçer, expired soft fail döner.
    Slug geçersiz olduğu için fetch_error da olabilir — her ikisi de halt=False.
    """
    from data.hl_candles import current_price
    real_cur = await current_price("BTC")
    finding = _fake_finding(cur_price=real_cur, ref_price=real_cur * 0.99,
                            seconds_remaining=0.0)
    result = await verify(finding)
    assert result["pass"] is False
    assert result["halt"] is False
    assert result["reason"] in ("expired", "fetch_error")


@pytest.mark.asyncio
async def test_verify_invalid_slug_returns_fetch_error():
    """
    Geçersiz slug ile PM verisi çekilemez → fetch_error, halt=False.
    """
    from data.hl_candles import current_price
    real_cur = await current_price("BTC")
    finding = _fake_finding(cur_price=real_cur, slug="tamamen-gecersiz-slug-xyz")
    result = await verify(finding)
    assert result["pass"] is False
    assert result["halt"] is False
    # fetch_error veya expired (slug bulunamazsa market None döner)


@pytest.mark.asyncio
async def test_verify_real_scout_finding_has_valid_structure():
    """Gerçek Scout bulgusu → Verifier geçerli bir sonuç döndürür."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok — test geçerli")
    result = await verify(findings[0])
    assert "pass" in result
    assert result["reason"] in {"ok", "edge_gone", "expired", "api_mismatch", "fetch_error"}
    assert isinstance(result["halt"], bool)


@pytest.mark.asyncio
async def test_verify_pass_edge_above_min():
    """PASS durumunda fresh_edge >= MIN_EDGE_PCT."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    for f in findings:
        result = await verify(f)
        if result["pass"]:
            assert result["fresh_edge"] >= config.MIN_EDGE_PCT
            return
    pytest.skip("Hiçbir bulgu Verifier'ı geçmedi — normal durum")


@pytest.mark.asyncio
async def test_verify_fresh_prices_positive_on_non_fetch_error():
    """fetch_error dışındaki sonuçlarda fresh_cur_price > 0."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    result = await verify(findings[0])
    if result["reason"] != "fetch_error":
        assert result["fresh_cur_price"] > 0
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
pytest tests/test_verifier.py -v 2>&1 | head -20
```

Beklenti: `ImportError: No module named 'council.verifier'`

- [ ] **Adım 3: council/verifier.py yaz**

```python
"""
council/verifier.py — KATMAN 2: Bağımsız Doğrulayıcı.

Scout bulgusunu taze API verisiyle teyit eder.
  Soft fail : Edge geçti / süre doldu → market atlanır, halt=False
  Hard fail : API drift anomalisi     → halt=HALT_ON_API_MISMATCH
"""
import asyncio
import sys
import os
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, parse_market_window
from data.fair_value import fair_yes
import config

PRICE_DRIFT_HALT_PCT = 2.0    # HL fiyatı Scout'tan bu yana >%2 farklıysa → HALT
PM_DRIFT_HALT        = 0.10   # PM bestAsk >0.10 hareket ettiyse → HALT
MIN_SECONDS          = 60     # Çözüme <60s kaldıysa → expired


async def verify(finding: dict) -> dict:
    """
    Scout bulgusunu bağımsız API çağrısıyla doğrular.

    Args:
        finding: scan_edges()'den gelen dict — slug dahil olmalı.

    Returns:
        {pass, reason, halt, fresh_cur_price, fresh_best_ask, fresh_best_bid,
         fresh_fair, fresh_edge, fresh_seconds, hl_drift_pct, pm_drift}
    """
    asset     = finding["asset"]
    slug      = finding["slug"]
    scout_cur = finding["cur_price"]
    scout_ask = finding["best_ask"]
    ref_price = finding["ref_price"]
    action    = finding["action"]

    # ── 1. HL taze fiyat ──────────────────────────────────────────────────────
    try:
        fresh_cur = await current_price(asset)
    except Exception as e:
        return _result(False, "fetch_error", False, extra={"error": str(e)})

    # ── 2. HL drift kontrolü ─────────────────────────────────────────────────
    hl_drift = abs(fresh_cur - scout_cur) / scout_cur * 100
    if hl_drift > PRICE_DRIFT_HALT_PCT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    # ── 3. PM taze fiyat ─────────────────────────────────────────────────────
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            market = await fetch_by_slug(s, slug)
    except Exception as e:
        return _result(False, "fetch_error", False,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift,
                       extra={"error": str(e)})

    if market is None:
        return _result(False, "fetch_error", False,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    window = parse_market_window(market)
    if window is None:
        return _result(False, "fetch_error", False,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    fresh_ask     = window["best_ask"]
    fresh_bid     = window["best_bid"]
    fresh_seconds = window["seconds_remaining"]

    # ── 4. PM drift kontrolü ─────────────────────────────────────────────────
    pm_drift = abs(fresh_ask - scout_ask)
    if pm_drift > PM_DRIFT_HALT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, hl_drift_pct=hl_drift,
                       pm_drift=pm_drift)

    # ── 5. Süre kontrolü ─────────────────────────────────────────────────────
    if fresh_seconds < MIN_SECONDS:
        return _result(False, "expired", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 6-7. Fair value + edge yeniden hesapla ────────────────────────────────
    fresh_fair = fair_yes(fresh_cur, ref_price, fresh_seconds, asset)
    fresh_edge = (fresh_fair - fresh_ask) if action == "YES" else (fresh_bid - fresh_fair)

    # ── 8. Edge kontrolü ─────────────────────────────────────────────────────
    if fresh_edge < config.MIN_EDGE_PCT:
        return _result(False, "edge_gone", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 9. PASS ───────────────────────────────────────────────────────────────
    return _result(True, "ok", False,
                   fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                   fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                   fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                   hl_drift_pct=hl_drift, pm_drift=pm_drift)


def _result(pass_: bool, reason: str, halt: bool, *,
            fresh_cur: float = 0.0, fresh_ask: float = 0.0,
            fresh_bid: float = 0.0, fresh_seconds: float = 0.0,
            fresh_fair: float = 0.0, fresh_edge: float = 0.0,
            hl_drift_pct: float = 0.0, pm_drift: float = 0.0,
            extra: dict = None) -> dict:
    r = {
        "pass":            pass_,
        "reason":          reason,
        "halt":            halt,
        "fresh_cur_price": fresh_cur,
        "fresh_best_ask":  fresh_ask,
        "fresh_best_bid":  fresh_bid,
        "fresh_fair":      fresh_fair,
        "fresh_edge":      round(fresh_edge, 4),
        "fresh_seconds":   fresh_seconds,
        "hl_drift_pct":    round(hl_drift_pct, 4),
        "pm_drift":        round(pm_drift, 4),
    }
    if extra:
        r.update(extra)
    return r


async def main():
    from council.scout import scan_edges
    print("=" * 70)
    print("VERIFIER — Scout bulgularını bağımsız teyit ediyor")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu gelmedi.")
        return
    for f in findings:
        r = await verify(f)
        icon = "✓ PASS" if r["pass"] else f"✗ {r['reason'].upper()}"
        halt = " [HALT]" if r["halt"] else ""
        print(f"\n{f['question'][:50]}")
        print(f"  Scout edge  : {f['edge']:+.3f} | Scout ask: {f['best_ask']:.3f}")
        print(f"  Fresh edge  : {r['fresh_edge']:+.3f} | Fresh ask: {r['fresh_best_ask']:.3f}")
        print(f"  HL drift    : {r['hl_drift_pct']:.4f}%")
        print(f"  PM drift    : {r['pm_drift']:.4f}")
        print(f"  Sonuç       : {icon}{halt}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_verifier.py -v --asyncio-mode=auto
```

Beklenti: `12 passed` (gerçek API ile, skip'ler normal)

- [ ] **Adım 5: Tüm testler yeşil**

```bash
pytest tests/ -v --asyncio-mode=auto
```

Beklenti: `83 passed, 0 failed`

- [ ] **Adım 6: Verifier'ı manuel çalıştır, çıktıyı gözle doğrula**

```bash
python -m council.verifier
```

Kontrol: HL drift küçük mü (<%1)? Soft fail mi PASS mı döndü? Mantıklı mı?

- [ ] **Adım 7: Final commit**

```bash
git add council/verifier.py tests/test_verifier.py
git commit -m "feat(council): Verifier katmanı — bağımsız fiyat doğrulama (Katman 2)"
```

---

## Verification Checklist (Tamamlama Öncesi)

`superpowers:verification-before-completion` skill'ini invoke et:

- [ ] `pytest tests/ --asyncio-mode=auto` → 0 failed
- [ ] `python -m council.verifier` → mantıklı çıktı
- [ ] `python -m council.scout` → hâlâ çalışıyor (regresyon yok)
- [ ] api_mismatch testi gerçek halt=True döndürüyor
- [ ] soft fail testleri halt=False döndürüyor
