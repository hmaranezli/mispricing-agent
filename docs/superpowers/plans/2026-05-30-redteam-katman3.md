# RedTeam (Katman 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scout + Verifier'dan geçen bulguya karşı şeytan avukatı olan RedTeam katmanını TDD ile yaz; 6 kontrol (spread, likidite, fee, zaman, edge sanity, hacim) ile veto/warning ayrımını uygula.

**Architecture:** Tek dosya `council/redteam.py`, tek async fonksiyon `redteam(finding, verification) → dict`. Gamma'dan slug ile bağımsız API çağrısı yapar. Scout ve Verifier'a dokunulmaz.

**Tech Stack:** Python 3.11, aiohttp, pytest-asyncio — yeni bağımlılık yok.

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|--------|-----------|
| `council/redteam.py` | **YENİ** | 6 kontrol, veto/warning ayrımı, fee hesabı |
| `tests/test_redteam.py` | **YENİ** | Unit + integration testler |

---

## Task 1: council/redteam.py — Şeytan Avukatı

**Files:**
- Create: `council/redteam.py`
- Create: `tests/test_redteam.py`

- [ ] **Adım 1: Tüm failing testleri yaz**

```python
# tests/test_redteam.py
"""
council/redteam.py testleri.
Unit testler sahte veri ile, integration testler gerçek API ile. Mock yok.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.redteam import (
    redteam, _parse_taker_fee, _fee_adjusted_edge, _result,
    SPREAD_VETO, LIQUIDITY_VETO_USD, MIN_THESIS_SECS, EDGE_SANITY_MAX,
)
from council.scout import scan_edges
from council.verifier import verify


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _fake_finding(slug="btc-updown-5m-1748571000", action="YES",
                  fair_value=0.65, edge=0.15,
                  cur_price=73_500.0, ref_price=73_000.0,
                  best_ask=0.47, best_bid=0.46, seconds_remaining=180.0):
    return {
        "question": "Bitcoin Up or Down - Test",
        "asset": "BTC", "slug": slug, "action": action,
        "edge": edge, "cur_price": cur_price, "ref_price": ref_price,
        "best_ask": best_ask, "best_bid": best_bid,
        "seconds_remaining": seconds_remaining,
        "fair_value": fair_value, "neg_risk": False,
    }


def _fake_verification(fresh_fair=0.65, fresh_edge=0.15,
                        fresh_seconds=180.0, fresh_ask=0.47, fresh_bid=0.46):
    return {
        "pass": True, "reason": "ok", "halt": False,
        "fresh_cur_price": 73_500.0,
        "fresh_best_ask": fresh_ask, "fresh_best_bid": fresh_bid,
        "fresh_fair": fresh_fair, "fresh_edge": fresh_edge,
        "fresh_seconds": fresh_seconds,
        "hl_drift_pct": 0.01, "pm_drift": 0.005,
    }


# ── Unit: _parse_taker_fee ────────────────────────────────────────────────────

def test_parse_taker_fee_1000_is_2pct():
    """Gamma takerBaseFee=1000 → %2 (Polymarket belgelenmiş fee)."""
    assert abs(_parse_taker_fee(1000) - 0.02) < 1e-6


def test_parse_taker_fee_none_defaults_to_2pct():
    assert _parse_taker_fee(None) == 0.02


def test_parse_taker_fee_unreasonable_defaults_to_2pct():
    """fee > %20 mantıksız → fallback 0.02."""
    assert _parse_taker_fee(999_999) == 0.02


# ── Unit: _fee_adjusted_edge ──────────────────────────────────────────────────

def test_fee_adjusted_edge_yes_less_than_gross():
    """Fee, YES edge'ini düşürür."""
    net = _fee_adjusted_edge(fair=0.65, ask=0.47, bid=0.46, action="YES", fee=0.02)
    assert abs(net - (0.65 * 0.98 - 0.47)) < 1e-6
    assert net < (0.65 - 0.47)  # fee sonrası gross'tan küçük


def test_fee_adjusted_edge_no():
    """NO edge fee sonrası doğru hesaplanır."""
    net = _fee_adjusted_edge(fair=0.35, ask=0.65, bid=0.60, action="NO", fee=0.02)
    assert abs(net - ((1 - 0.35) * 0.98 - (1 - 0.60))) < 1e-6


def test_fee_adjusted_edge_zero_fee_equals_gross():
    """Fee=0 → net == gross."""
    net = _fee_adjusted_edge(fair=0.65, ask=0.47, bid=0.46, action="YES", fee=0.0)
    assert abs(net - (0.65 - 0.47)) < 1e-6


# ── Unit: _result yapısı ──────────────────────────────────────────────────────

def test_result_has_required_fields():
    r = _result(True, [], [], 0.15, 0.02, 0.01, 5000.0)
    required = {"pass", "vetoes", "warnings", "fee_adj_edge",
                "taker_fee", "spread", "liquidity_usd"}
    assert required.issubset(set(r.keys()))


def test_result_pass_with_warning_no_veto():
    r = _result(True, [], ["low_volume"], 0.10, 0.02, 0.01, 5000.0)
    assert r["pass"] is True


def test_result_fail_with_veto():
    r = _result(False, ["spread_too_wide"], [], 0.10, 0.02, 0.99, 5000.0)
    assert r["pass"] is False
    assert "spread_too_wide" in r["vetoes"]


# ── Integration: gerçek API ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_veto_insufficient_time():
    """fresh_seconds=60 (< 120) → insufficient_time_for_thesis veto."""
    result = await redteam(
        _fake_finding(),
        _fake_verification(fresh_seconds=60.0),
    )
    assert "insufficient_time_for_thesis" in result["vetoes"]
    assert result["pass"] is False


@pytest.mark.asyncio
async def test_veto_edge_suspiciously_large():
    """fresh_edge=0.40 (> 0.35) → edge_suspiciously_large veto."""
    result = await redteam(
        _fake_finding(),
        _fake_verification(fresh_edge=0.40),
    )
    assert "edge_suspiciously_large" in result["vetoes"]
    assert result["pass"] is False


@pytest.mark.asyncio
async def test_veto_edge_killed_by_fee():
    """fair=0.50, ask=0.43 → gross=0.07, net=0.50*0.98-0.43≈0.059 < 0.08 → veto."""
    result = await redteam(
        _fake_finding(action="YES"),
        _fake_verification(fresh_fair=0.50, fresh_ask=0.43, fresh_edge=0.07),
    )
    assert "edge_killed_by_fee" in result["vetoes"]


@pytest.mark.asyncio
async def test_warning_alone_does_not_cause_fail():
    """Warning tek başına pass=False yapmaz."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    if result["warnings"] and not result["vetoes"]:
        assert result["pass"] is True


@pytest.mark.asyncio
async def test_real_pipeline_result_structure():
    """Scout → Verifier → RedTeam zinciri doğru yapı döndürür."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    required = {"pass", "vetoes", "warnings", "fee_adj_edge",
                "taker_fee", "spread", "liquidity_usd"}
    assert required.issubset(set(result.keys()))
    assert isinstance(result["vetoes"], list)
    assert isinstance(result["warnings"], list)


@pytest.mark.asyncio
async def test_fee_adj_edge_lte_gross_edge():
    """fee_adj_edge her zaman fresh_edge'den küçük veya eşit (fee ≥ 0)."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    if result["taker_fee"] > 0:
        assert result["fee_adj_edge"] <= v["fresh_edge"] + 1e-6
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_redteam.py -v 2>&1 | head -15
```

Beklenti: `ImportError: No module named 'council.redteam'`

- [ ] **Adım 3: council/redteam.py yaz**

```python
"""
council/redteam.py — KATMAN 3: Şeytan Avukatı.

"Bu işlemi neden YAPMAMALIYIZ?" sorusunu sorar.
Herhangi bir veto → pass=False. Warning'ler loglanır, bloklamaz.
"""
import asyncio
import sys
import os
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import fetch_by_slug
import config

SPREAD_VETO        = 0.05   # bid-ask spread > 5 cent → veto
LIQUIDITY_VETO_USD = 500    # CLOB likidite < $500 → veto
VOLUME_WARN_USD    = 50     # 24s hacim < $50 → warning (bloklamaz)
MIN_THESIS_SECS    = 120    # < 2dk → PM yeniden fiyatlanamaz → veto
EDGE_SANITY_MAX    = 0.35   # edge > %35 → veri hatası şüphesi → veto


def _parse_taker_fee(raw) -> float:
    """Gamma takerBaseFee → ondalık oran.
    Polymarket %2 fee → takerBaseFee=1000 → 1000/50000 = 0.02.
    """
    try:
        fee = float(raw) / 50_000
        return fee if 0 < fee <= 0.20 else 0.02
    except (TypeError, ValueError):
        return 0.02


def _fee_adjusted_edge(fair: float, ask: float, bid: float,
                        action: str, fee: float) -> float:
    """
    Fee sonrası gerçek edge.
    YES: fair × (1−fee) − ask
    NO:  (1−fair) × (1−fee) − (1−bid)
    """
    if action == "YES":
        return fair * (1 - fee) - ask
    return (1 - fair) * (1 - fee) - (1 - bid)


def _result(pass_: bool, vetoes: list, warnings: list,
            fee_adj: float, taker_fee: float,
            spread: float, liquidity: float) -> dict:
    return {
        "pass":          pass_,
        "vetoes":        vetoes,
        "warnings":      warnings,
        "fee_adj_edge":  round(fee_adj, 4),
        "taker_fee":     round(taker_fee, 4),
        "spread":        spread,
        "liquidity_usd": liquidity,
    }


async def redteam(finding: dict, verification: dict) -> dict:
    """
    Bulguya karşı şeytan avukatlığı yapar.

    Args:
        finding:      Scout scan_edges() çıktısı (slug, action dahil)
        verification: Verifier verify() çıktısı (fresh_fair, fresh_edge, fresh_seconds dahil)

    Returns:
        {pass, vetoes, warnings, fee_adj_edge, taker_fee, spread, liquidity_usd}
    """
    vetoes   = []
    warnings = []

    # ── Gamma'dan taze market verisi ─────────────────────────────────────────
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            market = await fetch_by_slug(s, finding["slug"])
    except Exception:
        market = None

    if market is None:
        return _result(False, ["fetch_error"], [], 0.0, 0.02, 0.0, 0.0)

    try:
        spread      = float(market.get("spread") or 999)
        liquidity   = float(market.get("liquidityClob") or 0)
        volume_24hr = float(market.get("volume24hr") or 0)
        taker_fee   = _parse_taker_fee(market.get("takerBaseFee"))
    except (TypeError, ValueError):
        return _result(False, ["parse_error"], [], 0.0, 0.02, 0.0, 0.0)

    # ── 1. Spread kontrolü ────────────────────────────────────────────────────
    if spread > SPREAD_VETO:
        vetoes.append("spread_too_wide")

    # ── 2. Likidite kontrolü ─────────────────────────────────────────────────
    if liquidity < LIQUIDITY_VETO_USD:
        vetoes.append("liquidity_insufficient")

    # ── 3. Hacim uyarısı ─────────────────────────────────────────────────────
    if volume_24hr < VOLUME_WARN_USD:
        warnings.append("low_volume")

    # ── 4. Zaman kontrolü ────────────────────────────────────────────────────
    if verification["fresh_seconds"] < MIN_THESIS_SECS:
        vetoes.append("insufficient_time_for_thesis")

    # ── 5. Fee sonrası edge kontrolü ─────────────────────────────────────────
    fee_adj = _fee_adjusted_edge(
        fair=verification["fresh_fair"],
        ask=verification["fresh_best_ask"],
        bid=verification["fresh_best_bid"],
        action=finding["action"],
        fee=taker_fee,
    )
    if fee_adj < config.MIN_EDGE_PCT:
        vetoes.append("edge_killed_by_fee")

    # ── 6. Edge sağlık kontrolü ───────────────────────────────────────────────
    if verification["fresh_edge"] > EDGE_SANITY_MAX:
        vetoes.append("edge_suspiciously_large")

    return _result(len(vetoes) == 0, vetoes, warnings,
                   fee_adj, taker_fee, spread, liquidity)


async def main():
    from council.scout import scan_edges
    from council.verifier import verify
    print("=" * 70)
    print("REDTEAM — şeytan avukatı kontrolü")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu yok.")
        return
    for f in findings:
        v = await verify(f)
        if not v["pass"]:
            print(f"\n{f['question'][:50]} → Verifier geçmedi: {v['reason']}")
            continue
        r = await redteam(f, v)
        icon = "PASS" if r["pass"] else f"VETO [{', '.join(r['vetoes'])}]"
        print(f"\n{f['question'][:50]}")
        print(f"  Gross edge    : {v['fresh_edge']:+.3f}")
        print(f"  Fee-adj edge  : {r['fee_adj_edge']:+.3f}  (fee: {r['taker_fee']:.1%})")
        print(f"  Spread        : {r['spread']:.3f}  |  Likidite: ${r['liquidity_usd']:,.0f}")
        if r["warnings"]:
            print(f"  Uyarılar      : {', '.join(r['warnings'])}")
        print(f"  Karar         : {icon}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_redteam.py -v --asyncio-mode=auto
```

Beklenti: `15 passed` (skip'ler aktif market yokken normal)

- [ ] **Adım 5: Tüm test suite'i çalıştır**

```bash
pytest tests/ -v --asyncio-mode=auto
```

Beklenti: `88 passed, 0 failed`

- [ ] **Adım 6: Manuel çalıştır, çıktıyı gözle doğrula**

```bash
python -m council.redteam
```

Kontrol:
- fee_adj_edge < gross edge mi? (fee düşürüyor mu?)
- taker_fee 0.02 civarında mı?
- spread ve liquidity mantıklı mı?

- [ ] **Adım 7: Final commit**

```bash
git add council/redteam.py tests/test_redteam.py
git commit -m "feat(council): RedTeam katmanı — şeytan avukatı veto sistemi (Katman 3)"
```

---

## Verification Checklist

`superpowers:verification-before-completion` invoke et:

- [ ] `pytest tests/ --asyncio-mode=auto` → 0 failed
- [ ] `python -m council.redteam` → mantıklı çıktı
- [ ] `python -m council.scout` ve `python -m council.verifier` hâlâ çalışıyor (regresyon yok)
- [ ] `fee_adj_edge <= fresh_edge` her zaman (fee negatif değil)
- [ ] Veto olan bulguda `pass=False`, warning olup veto olmayan bulguda `pass=True`
