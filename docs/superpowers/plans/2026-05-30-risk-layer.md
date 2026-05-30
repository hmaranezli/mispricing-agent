# Risk Katmanı (Katman 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `council/risk.py` — Kelly fraksiyonu ile pozisyon boyutlandırması; günlük kayıp / pozisyon limiti / insan onayı kontrolü. Saf fonksiyon, sıfır API çağrısı.

**Architecture:** Pure function. Tüm dış durum (bankroll, açık pozisyon sayısı, günlük kayıp) parametre olarak enjekte edilir. `_kelly()` helper ile YES/NO Kelly hesabı, ardından 5 adım veto zinciri. `main()` manuel test için pipeline'ı çalıştırır.

**Tech Stack:** Python 3.12, pytest, config.py guardrail sabitleri (değiştirilmez).

---

## Dosya Yapısı

| Dosya | İşlem | Sorumluluk |
|-------|--------|------------|
| `council/risk.py` | Oluştur | `_kelly()`, `_result()`, `risk()`, `main()` |
| `tests/test_risk.py` | Oluştur | 14 senkron unit test, sıfır API çağrısı |

---

## Sabit Referanslar (config.py'den, değiştirme)

```python
config.DAILY_LOSS_LIMIT_PCT  = 0.10   # %10
config.MAX_OPEN_POSITIONS    = 5
config.MIN_EDGE_PCT          = 0.08   # %8
config.MAX_TRADE_PCT         = 0.05   # %5
config.HUMAN_APPROVAL_USD    = 50     # $50
```

---

## Task 1: Skeleton + Output Şeması Testi

**Files:**
- Create: `council/risk.py`
- Create: `tests/test_risk.py`

- [ ] **Step 1: `tests/test_risk.py` dosyasını oluştur**

```python
"""tests/test_risk.py — Katman 4 Risk birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.risk import risk, _kelly, KELLY_FRACTION, MIN_POSITION_USD


# ── Test fixture'ları ─────────────────────────────────────────────────────────

def _finding(action="YES", best_ask=0.40, best_bid=0.38):
    return {
        "question": "Will BTC go up?",
        "slug": "btc-up-1h",
        "asset": "BTC",
        "action": action,
        "fair": 0.55,
        "best_ask": best_ask,
        "best_bid": best_bid,
        "edge": 0.15,
        "cur_price": 65000.0,
        "ref_price": 64000.0,
        "seconds_remaining": 900,
    }


def _verification(fresh_fair=0.55, fresh_edge=0.15,
                  fresh_best_ask=0.40, fresh_best_bid=0.38,
                  fresh_seconds=300):
    return {
        "pass": True,
        "reason": "ok",
        "halt": False,
        "fresh_cur_price": 65000.0,
        "fresh_best_ask": fresh_best_ask,
        "fresh_best_bid": fresh_best_bid,
        "fresh_fair": fresh_fair,
        "fresh_edge": fresh_edge,
        "fresh_seconds": fresh_seconds,
        "hl_drift_pct": 0.01,
        "pm_drift": 0.005,
    }


def _redteam(fee_adj_edge=0.12):
    return {
        "pass": True,
        "vetoes": [],
        "warnings": [],
        "fee_adj_edge": fee_adj_edge,
        "taker_fee": 0.02,
        "spread": 0.02,
        "liquidity_usd": 5000.0,
    }


BANKROLL = 1000.0


# ── Task 1: output şeması ─────────────────────────────────────────────────────

def test_result_has_required_fields():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert "pass" in r
    assert "position_usd" in r
    assert "kelly_f" in r
    assert "kelly_fraction_applied" in r
    assert "requires_human_approval" in r
    assert "halt" in r
    assert "reason" in r
```

- [ ] **Step 2: Testi çalıştır — FAIL bekleniyor**

```bash
cd /root/mispricing_agent && source venv/bin/activate && pytest tests/test_risk.py::test_result_has_required_fields -v
```

Beklenen çıktı: `ERROR` veya `ModuleNotFoundError: No module named 'council.risk'`

- [ ] **Step 3: `council/risk.py` skeleton'ını oluştur**

```python
"""
council/risk.py — KATMAN 4: Risk Değerlendirmesi.

"Ne kadar?" sorusunu cevaplar.
Kelly fraksiyonu ile pozisyon boyutlandırır; sistem limitlerini ve
insan onayı koşullarını kontrol eder.

Saf fonksiyon — API çağrısı yok, DB bağlantısı yok.
Tüm dış durum (bankroll, açık pozisyonlar, günlük kayıp) parametre olarak gelir.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

KELLY_FRACTION   = 0.25  # Çeyrek Kelly — tam Kelly'nin 1/4'ü
MIN_POSITION_USD = 5.0   # Bu altı → fee'ye değmez → veto


def _kelly(action: str, fee_adj_edge: float,
           fresh_ask: float, fresh_bid: float) -> float:
    """Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0."""
    return 0.0  # Task 2'de implement edilecek


def _result(pass_: bool, position_usd: float = 0.0, kelly_f: float = 0.0,
            requires_human_approval: bool = False,
            halt: bool = False, reason: str = "") -> dict:
    return {
        "pass":                    pass_,
        "position_usd":            round(position_usd, 2),
        "kelly_f":                 round(kelly_f, 4),
        "kelly_fraction_applied":  KELLY_FRACTION,
        "requires_human_approval": requires_human_approval,
        "halt":                    halt,
        "reason":                  reason,
    }


def risk(
    finding:        dict,
    verification:   dict,
    redteam:        dict,
    bankroll_usd:   float,
    open_positions: int,
    daily_loss_usd: float,
) -> dict:
    """
    Pozisyon boyutlandırması ve sistem limiti kontrolü.

    Args:
        finding:        Scout scan_edges() çıktısı
        verification:   Verifier verify() çıktısı (fresh_best_ask/bid buradan)
        redteam:        RedTeam redteam() çıktısı (fee_adj_edge buradan)
        bankroll_usd:   Mevcut sermaye (USD)
        open_positions: Açık pozisyon sayısı
        daily_loss_usd: Bugünkü gerçekleşmiş kayıp (USD)

    Returns:
        {pass, position_usd, kelly_f, kelly_fraction_applied,
         requires_human_approval, halt, reason}
    """
    return _result(False, reason="not_implemented")
```

- [ ] **Step 4: Testi çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_result_has_required_fields -v
```

Beklenen: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "test(risk): skeleton ve output şeması testi — Katman 4 başlangıcı"
```

---

## Task 2: `_kelly()` — YES ve NO Kolları

**Files:**
- Modify: `council/risk.py` — `_kelly()` implement et
- Modify: `tests/test_risk.py` — 2 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testleri ekle**

`test_result_has_required_fields` fonksiyonunun altına:

```python
# ── Task 2: _kelly() hesabı ───────────────────────────────────────────────────

def test_kelly_yes_calculation():
    # edge=0.12, fresh_ask=0.40 → denom=0.60 → kelly=0.12/0.60=0.20
    k = _kelly("YES", fee_adj_edge=0.12, fresh_ask=0.40, fresh_bid=0.38)
    assert abs(k - 0.20) < 1e-6


def test_kelly_no_calculation():
    # edge=0.10, fresh_bid=0.40 → kelly=0.10/0.40=0.25
    k = _kelly("NO", fee_adj_edge=0.10, fresh_ask=0.60, fresh_bid=0.40)
    assert abs(k - 0.25) < 1e-6
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_kelly_yes_calculation tests/test_risk.py::test_kelly_no_calculation -v
```

Beklenen: Her ikisi `FAILED` (stub her zaman 0.0 döner)

- [ ] **Step 3: `council/risk.py`'de `_kelly()` implement et**

`_kelly` fonksiyonunu şununla değiştir:

```python
def _kelly(action: str, fee_adj_edge: float,
           fresh_ask: float, fresh_bid: float) -> float:
    """Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0."""
    if action == "YES":
        denom = 1.0 - fresh_ask
        return fee_adj_edge / denom if denom >= 0.01 else 0.0
    else:  # NO
        denom = fresh_bid
        return fee_adj_edge / denom if denom >= 0.01 else 0.0
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_kelly_yes_calculation tests/test_risk.py::test_kelly_no_calculation -v
```

Beklenen: Her ikisi `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): _kelly() YES/NO binary formülü — Task 2"
```

---

## Task 3: Günlük Kayıp Limiti (Halt)

**Files:**
- Modify: `council/risk.py` — halt kontrolü ekle
- Modify: `tests/test_risk.py` — 2 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testleri ekle**

```python
# ── Task 3: günlük kayıp limiti ───────────────────────────────────────────────

def test_halt_on_daily_loss_limit():
    # Tam limit: bankroll × DAILY_LOSS_LIMIT_PCT = 1000 × 0.10 = $100
    loss = BANKROLL * config.DAILY_LOSS_LIMIT_PCT
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=loss)
    assert r["pass"] is False
    assert r["halt"] is True
    assert r["reason"] == "daily_loss_limit_hit"


def test_no_halt_below_limit():
    # %9 kayıp → limit altı
    loss = BANKROLL * (config.DAILY_LOSS_LIMIT_PCT - 0.01)
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=loss)
    assert r["halt"] is False
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_halt_on_daily_loss_limit tests/test_risk.py::test_no_halt_below_limit -v
```

Beklenen: `test_halt_on_daily_loss_limit` → FAILED (halt bekleniyor, stub False döner)

- [ ] **Step 3: `risk()` içinde halt kontrolü ekle**

`risk()` fonksiyonundaki `return _result(False, reason="not_implemented")` satırını şununla değiştir:

```python
    # 1. Günlük kayıp limiti — HALT
    if bankroll_usd > 0 and daily_loss_usd / bankroll_usd >= config.DAILY_LOSS_LIMIT_PCT:
        return _result(False, halt=True, reason="daily_loss_limit_hit")

    return _result(False, reason="not_implemented")
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_halt_on_daily_loss_limit tests/test_risk.py::test_no_halt_below_limit -v
```

Beklenen: Her ikisi `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): günlük kayıp limiti halt kontrolü — Task 3"
```

---

## Task 4: Açık Pozisyon Limiti

**Files:**
- Modify: `council/risk.py` — pozisyon limiti ekle
- Modify: `tests/test_risk.py` — 2 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testleri ekle**

```python
# ── Task 4: açık pozisyon limiti ─────────────────────────────────────────────

def test_veto_max_open_positions():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL,
             open_positions=config.MAX_OPEN_POSITIONS,
             daily_loss_usd=0.0)
    assert r["pass"] is False
    assert r["reason"] == "max_open_positions_reached"
    assert r["halt"] is False


def test_pass_below_max_positions():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL,
             open_positions=config.MAX_OPEN_POSITIONS - 1,
             daily_loss_usd=0.0)
    # Henüz not_implemented döner ama halt ve reason kontrol ediyoruz
    assert r["halt"] is False
    assert r["reason"] != "max_open_positions_reached"
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_veto_max_open_positions tests/test_risk.py::test_pass_below_max_positions -v
```

Beklenen: `test_veto_max_open_positions` → FAILED

- [ ] **Step 3: `risk()` içinde pozisyon limiti ekle**

Halt kontrolünden hemen sonraya ekle (`return _result(False, reason="not_implemented")` öncesine):

```python
    # 2. Açık pozisyon limiti
    if open_positions >= config.MAX_OPEN_POSITIONS:
        return _result(False, reason="max_open_positions_reached")
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_veto_max_open_positions tests/test_risk.py::test_pass_below_max_positions -v
```

Beklenen: Her ikisi `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): açık pozisyon limiti kontrolü — Task 4"
```

---

## Task 5: Edge Geçerlilik Kontrolü

**Files:**
- Modify: `council/risk.py` — edge çift emniyet kontrolü ekle
- Modify: `tests/test_risk.py` — 1 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testi ekle**

```python
# ── Task 5: edge geçerlilik ───────────────────────────────────────────────────

def test_veto_edge_below_minimum():
    # fee_adj_edge tam MIN_EDGE_PCT altında
    rt = _redteam(fee_adj_edge=config.MIN_EDGE_PCT - 0.001)
    r = risk(_finding(), _verification(), rt,
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert r["pass"] is False
    assert r["reason"] == "edge_below_minimum"
```

- [ ] **Step 2: Testi çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_veto_edge_below_minimum -v
```

Beklenen: `FAILED`

- [ ] **Step 3: `risk()` içinde edge kontrolü ekle**

Pozisyon limiti bloğundan sonraya ekle:

```python
    # 3. Edge geçerlilik — çift emniyet (RedTeam zaten kontrol etti)
    fee_adj_edge = redteam["fee_adj_edge"]
    if fee_adj_edge < config.MIN_EDGE_PCT:
        return _result(False, reason="edge_below_minimum")
```

- [ ] **Step 4: Testi çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_veto_edge_below_minimum -v
```

Beklenen: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): edge geçerlilik çift emniyet kontrolü — Task 5"
```

---

## Task 6: Kelly Hesabı + Cap + Minimum Pozisyon + Sıfır Bölen

**Files:**
- Modify: `council/risk.py` — Kelly hesabı ve pozisyon kontrolü ekle
- Modify: `tests/test_risk.py` — 3 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testleri ekle**

```python
# ── Task 6: Kelly hesabı + cap + min pozisyon ─────────────────────────────────

def test_kelly_capped_at_max_trade_pct():
    # edge=0.50, fresh_ask=0.10 → kelly=0.50/0.90=0.556
    # × KELLY_FRACTION(0.25) = 0.139 > MAX_TRADE_PCT(0.05) → cap
    # position = 0.05 × 1000 = $50.00
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is True
    assert abs(r["position_usd"] - BANKROLL * config.MAX_TRADE_PCT) < 0.01


def test_veto_position_too_small():
    # bankroll=$10, edge=MIN_EDGE_PCT=0.08, fresh_ask=0.40
    # kelly = 0.08/0.60 = 0.133 → × 0.25 = 0.033 → $0.33 < MIN_POSITION_USD($5)
    r = risk(
        _finding(action="YES", best_ask=0.40),
        _verification(fresh_best_ask=0.40, fresh_edge=config.MIN_EDGE_PCT),
        _redteam(fee_adj_edge=config.MIN_EDGE_PCT),
        bankroll_usd=10.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is False
    assert r["reason"] == "position_too_small"


def test_kelly_zero_denom_vetoes():
    # fresh_ask=0.999 → denom=0.001 < 0.01 → kelly=0.0 → position=$0 < $5 → veto
    r = risk(
        _finding(action="YES", best_ask=0.999),
        _verification(fresh_best_ask=0.999, fresh_edge=0.12),
        _redteam(fee_adj_edge=0.12),
        bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is False
    assert r["reason"] == "position_too_small"
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_kelly_capped_at_max_trade_pct tests/test_risk.py::test_veto_position_too_small tests/test_risk.py::test_kelly_zero_denom_vetoes -v
```

Beklenen: Üçü de `FAILED`

- [ ] **Step 3: `risk()` içinde Kelly bloğunu ekle**

Edge kontrolünden sonraya ekle, `return _result(False, reason="not_implemented")` yerine:

```python
    # 4. Kelly hesabı ve minimum pozisyon
    kelly_f = _kelly(
        action=finding["action"],
        fee_adj_edge=fee_adj_edge,
        fresh_ask=verification["fresh_best_ask"],
        fresh_bid=verification["fresh_best_bid"],
    )
    capped_f     = min(kelly_f * KELLY_FRACTION, config.MAX_TRADE_PCT)
    position_usd = capped_f * bankroll_usd

    if position_usd < MIN_POSITION_USD:
        return _result(False, kelly_f=kelly_f, reason="position_too_small")

    return _result(False, reason="not_implemented")
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_kelly_capped_at_max_trade_pct tests/test_risk.py::test_veto_position_too_small tests/test_risk.py::test_kelly_zero_denom_vetoes -v
```

Beklenen: Üçü de `PASSED`

- [ ] **Step 5: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): Kelly hesabı, MAX_TRADE_PCT cap, minimum pozisyon — Task 6"
```

---

## Task 7: İnsan Onayı Bayrağı + Normal Geçiş

**Files:**
- Modify: `council/risk.py` — onay bayrağı + pass döndür
- Modify: `tests/test_risk.py` — 3 test ekle

- [ ] **Step 1: `tests/test_risk.py`'ye testleri ekle**

```python
# ── Task 7: insan onayı + normal geçiş ───────────────────────────────────────

def test_human_approval_flag_set():
    # bankroll=$10000 → position = min(0.556×0.25, 0.05) × 10000 = $500 > $50
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=10_000.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["requires_human_approval"] is True


def test_human_approval_does_not_veto():
    # Büyük pozisyon → bayrak kalkar ama PASS=True
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=10_000.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is True
    assert r["requires_human_approval"] is True


def test_pass_normal_case():
    # bankroll=1000, edge=0.12, ask=0.40
    # kelly=0.20 → ×0.25=0.05 → position=$50 (= HUMAN_APPROVAL_USD, > değil)
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert r["pass"] is True
    assert r["position_usd"] > 0
    assert r["kelly_f"] > 0
    assert r["kelly_fraction_applied"] == KELLY_FRACTION
    assert r["halt"] is False
    assert r["reason"] == ""
    assert r["requires_human_approval"] is False
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_risk.py::test_human_approval_flag_set tests/test_risk.py::test_human_approval_does_not_veto tests/test_risk.py::test_pass_normal_case -v
```

Beklenen: Üçü de `FAILED` (stub hâlâ `not_implemented` döner)

- [ ] **Step 3: `risk()` sonunu tamamla**

`return _result(False, reason="not_implemented")` satırını şununla değiştir:

```python
    # 5. İnsan onayı bayrağı (veto değil — Gate handle eder)
    requires_human_approval = position_usd > config.HUMAN_APPROVAL_USD

    return _result(
        pass_=True,
        position_usd=position_usd,
        kelly_f=kelly_f,
        requires_human_approval=requires_human_approval,
        reason="",
    )
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_risk.py::test_human_approval_flag_set tests/test_risk.py::test_human_approval_does_not_veto tests/test_risk.py::test_pass_normal_case -v
```

Beklenen: Üçü de `PASSED`

- [ ] **Step 5: Tüm risk testlerini çalıştır**

```bash
pytest tests/test_risk.py -v
```

Beklenen: `14 passed, 0 skipped`

- [ ] **Step 6: Commit**

```bash
git add council/risk.py tests/test_risk.py
git commit -m "feat(risk): insan onayı bayrağı, risk() tamamlandı — Task 7"
```

---

## Task 8: `main()` + Tam Test Koşusu

**Files:**
- Modify: `council/risk.py` — `main()` ekle

- [ ] **Step 1: `council/risk.py`'nin sonuna `main()` ekle**

Mevcut son satırın (`return _result(...)`) altına:

```python


async def main():
    """Manuel test: Scout→Verifier→RedTeam→Risk zincirini çalıştırır."""
    import asyncio
    from council.scout import scan_edges
    from council.verifier import verify
    from council.redteam import redteam as rt

    print("=" * 70)
    print("RISK — pozisyon boyutlandırma")
    print("=" * 70)

    bankroll = getattr(config, "STARTING_CAPITAL_USD", 1000.0)

    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu yok.")
        return

    for f in findings:
        v = await verify(f)
        if not v["pass"]:
            print(f"\n{f['question'][:50]} → Verifier: {v['reason']}")
            continue
        r = await rt(f, v)
        if not r["pass"]:
            print(f"\n{f['question'][:50]} → RedTeam veto: {r['vetoes']}")
            continue
        rk = risk(f, v, r,
                  bankroll_usd=bankroll, open_positions=0, daily_loss_usd=0.0)
        icon = "PASS" if rk["pass"] else f"VETO [{rk['reason']}]"
        print(f"\n{f['question'][:50]}")
        print(f"  Kelly (ham)   : {rk['kelly_f']:.3f}")
        print(f"  Pozisyon      : ${rk['position_usd']:.2f}")
        if rk["requires_human_approval"]:
            print("  *** İNSAN ONAYI GEREKLİ ***")
        if rk["halt"]:
            print("  *** SİSTEM DURDU — günlük kayıp limiti ***")
        print(f"  Karar         : {icon}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 2: Tam test suite'ini çalıştır**

```bash
pytest tests/ --asyncio-mode=auto -v
```

Beklenen: En az `96 passed` (önceki 82 + yeni 14), `0 failed`

- [ ] **Step 3: Final commit**

```bash
git add council/risk.py
git commit -m "feat(council): Risk katmanı — Kelly sizing + sistem limitleri (Katman 4)"
```

---

## Doğrulama

Tüm tasklar bittikten sonra:

```bash
pytest tests/test_risk.py -v --tb=short
```

Beklenen çıktı:
```
tests/test_risk.py::test_result_has_required_fields PASSED
tests/test_risk.py::test_kelly_yes_calculation PASSED
tests/test_risk.py::test_kelly_no_calculation PASSED
tests/test_risk.py::test_halt_on_daily_loss_limit PASSED
tests/test_risk.py::test_no_halt_below_limit PASSED
tests/test_risk.py::test_veto_max_open_positions PASSED
tests/test_risk.py::test_pass_below_max_positions PASSED
tests/test_risk.py::test_veto_edge_below_minimum PASSED
tests/test_risk.py::test_kelly_capped_at_max_trade_pct PASSED
tests/test_risk.py::test_veto_position_too_small PASSED
tests/test_risk.py::test_kelly_zero_denom_vetoes PASSED
tests/test_risk.py::test_human_approval_flag_set PASSED
tests/test_risk.py::test_human_approval_does_not_veto PASSED
tests/test_risk.py::test_pass_normal_case PASSED

14 passed, 0 skipped, 0 failed
```
