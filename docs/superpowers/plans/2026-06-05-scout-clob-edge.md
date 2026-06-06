# Scout CLOB Edge Entegrasyonu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scout, edge hesabını stale market API yerine CLOB gerçek zamanlı fiyatıyla yapar → Verifier CLOB kontrolünü kaldırır, sadece HL drift kontrolü yapar → council gecikmesi 10-20s'den 2-4s'ye düşer, gerçek edge'li trade'ler açılır.

**Architecture:** `_process_market()` içinde market API'den timing/token_id alındıktan sonra `get_clob_price(yes_token_id)` çağrılır. CLOB fiyatı `best_ask` olur, `1 - clob_yes` approximation `best_bid` olur. Edge bu gerçek fiyatla hesaplanır. Verifier'da artık CLOB çağrısı yok — sadece HL drift kontrolü yapılır ve scout'un CLOB fiyatları pass-through edilir.

**Tech Stack:** Python asyncio, aiohttp, pytest-asyncio, unittest.mock

---

### Task 1: Scout — CLOB fiyatıyla edge hesabı

**Files:**
- Modify: `council/scout.py` (`_process_market` fonksiyonu, ~satır 62-117)
- Modify: `tests/test_scout.py` (mevcut testlere `get_clob_price` mock eklenir, 2 yeni test eklenir)

**Bağlam:** Şu an `_process_market()` market API'nin `window["best_ask"]`/`window["best_bid"]`'ini kullanıyor (stale). `get_clob_price(yes_token_id)` zaten `data.clob_price` modülünde mevcut. `yes_token_id` ve `no_token_id` market API'den çekiliyor ve finding'de yer alıyor.

Edge hesabı:
- `clob_yes = get_clob_price(yes_token_id)` → YES ask (CLOB gerçek fiyat)
- `clob_bid = max(0.0, 1.0 - clob_yes)` → YES bid approximation (binary: YES + NO ≈ 1)
- `edge = fair_yes - clob_yes` (YES) veya `clob_bid - fair_yes` (NO)
- CLOB None → market atlanır

- [ ] **Step 1: Failing testleri yaz**

`tests/test_scout.py` dosyasını oku. Mevcut test yapısını anla. Dosyanın sonuna ekle:

```python
# ── CLOB fiyat testleri ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_market_uses_clob_price_not_market_api():
    """_process_market CLOB fiyatını kullanır, market API best_ask'ı değil."""
    from council.scout import _process_market
    # market API best_ask=0.80 (stale), CLOB gerçek=0.55 → edge = fair-0.55
    market = _fake_market(best_ask=0.80, best_bid=0.79, seconds=300)
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.55), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=100_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=104_000.0), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        result = await _process_market(market)
    assert result is not None
    assert abs(result["best_ask"] - 0.55) < 1e-6, "best_ask CLOB fiyatı olmalı"


@pytest.mark.asyncio
async def test_process_market_returns_none_when_no_clob_liquidity():
    """CLOB None döndürünce (likidite yok) market atlanır."""
    from council.scout import _process_market
    market = _fake_market(best_ask=0.35, best_bid=0.34, seconds=300)
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=None), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=100_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=104_000.0):
        result = await _process_market(market)
    assert result is None, "CLOB likidite yoksa market atlanmalı"
```

Not: `_fake_market()` helper mevcut test dosyasında zaten varsa onu kullan. Yoksa şu şekilde yaz:

```python
def _fake_market(best_ask=0.35, best_bid=0.34, seconds=300, asset="BTC"):
    """Test için sahte market dict."""
    import time
    start_ms = int((time.time() - seconds) * 1000)
    return {
        "question": f"{asset} Up or Down - Test",
        "slug": f"{asset.lower()}-updown-5m-9999999",
        "groupItemTitle": "Up",
        "clobTokenIds": '["yes-tok-111","no-tok-222"]',
        "bestAsk": str(best_ask),
        "bestBid": str(best_bid),
        "negRisk": False,
        "endDate": "2099-01-01T00:00:00Z",
        "eventStartTime": "2099-01-01T00:00:00Z",
        "startDate": "2099-01-01T00:00:00Z",
    }
```

- [ ] **Step 2: Testlerin kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_scout.py::test_process_market_uses_clob_price_not_market_api \
       tests/test_scout.py::test_process_market_returns_none_when_no_clob_liquidity \
       -v 2>&1 | tail -10
```
Expected: `FAILED` — `get_clob_price` scout'ta henüz import edilmedi.

- [ ] **Step 3: `council/scout.py`'yi güncelle**

Şu satırı ekle (import bloğunun sonuna):
```python
from data.clob_price import get_clob_price
```

`_process_market` fonksiyonunda şu bloğu bul (satır ~81-93):
```python
    if window["best_ask"] <= 0 or window["best_bid"] <= 0:
        return None

    try:
        ref_price = await price_at_timestamp(asset, window["start_ms"])
        cur       = await current_price(asset)
    except (ValueError, Exception):
        return None

    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset)
    signal = _edge_signal(fair, window["best_ask"], window["best_bid"])
    if signal is None:
        return None

    _tids = _parse_token_ids(m.get("clobTokenIds"))
    yes_token = _tids[0] if _tids else None
    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02
```

Bunu şu şekilde değiştir:
```python
    _tids = _parse_token_ids(m.get("clobTokenIds"))
    yes_token = _tids[0] if _tids else None
    no_token  = _tids[1] if len(_tids) > 1 else None

    # CLOB gerçek zamanlı fiyat — market API bestAsk stale olduğundan kullanmıyoruz
    clob_yes = await get_clob_price(yes_token) if yes_token else None
    if clob_yes is None:
        return None  # CLOB likidite yok → atla

    clob_ask = clob_yes                          # YES almak için ödeyeceğimiz fiyat
    clob_bid = max(0.0, 1.0 - clob_yes)         # YES satmak için alacağımız fiyat (binary approximation)

    try:
        ref_price = await price_at_timestamp(asset, window["start_ms"])
        cur       = await current_price(asset)
    except (ValueError, Exception):
        return None

    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset)
    signal = _edge_signal(fair, clob_ask, clob_bid)
    if signal is None:
        return None

    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02
```

Return bloğunu da güncelle (satır ~99-117), `window["best_ask"]`/`window["best_bid"]`'i CLOB fiyatlarıyla değiştir:
```python
    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          clob_ask,       # CLOB gerçek fiyat (market API değil)
        "best_bid":          clob_bid,       # 1 - clob_yes approximation
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
        "slug":              m.get("slug", ""),
        "_window":           window,
        "_raw_market":       m,
        "yes_token_id":      yes_token,
        "no_token_id":       no_token,
        "taker_fee":         taker_fee,
    }
```

Ayrıca `window["best_ask"] <= 0 or window["best_bid"] <= 0:` kontrolünü kaldır (artık CLOB None kontrolü yapıyor).

- [ ] **Step 4: Yeni testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_scout.py::test_process_market_uses_clob_price_not_market_api \
       tests/test_scout.py::test_process_market_returns_none_when_no_clob_liquidity \
       -v 2>&1 | tail -10
```
Expected: `2 passed`

- [ ] **Step 5: Mevcut scout testlerini güncelle**

```bash
pytest tests/test_scout.py -v 2>&1 | tail -20
```

Kırılan testler için: `get_clob_price` mock'u eksik. Her kırık test için:
```python
patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.40)
```
ekle. `return_value=0.40` mevcut testin amacını değiştirmeyen uygun bir CLOB fiyatıdır.

Ayrıca `best_ask` ve `best_bid` assertion'larını kontrol et: artık CLOB fiyatı (0.40) ve `1-0.40=0.60` olacak. Test assertion'larını güncelle.

- [ ] **Step 6: Tüm scout testleri yeşil**

```bash
pytest tests/test_scout.py -v 2>&1 | tail -10
```
Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add council/scout.py tests/test_scout.py
git commit -m "feat(scout): CLOB gerçek zamanlı fiyatıyla edge hesabı

market API bestAsk (10-30s stale) yerine CLOB /price kullanılıyor.
CLOB None → market atlanır (likidite yok).
Verifier artık CLOB'u tekrar kontrol etmeyecek — scout zaten yaptı."
```

---

### Task 2: Verifier — Sadece HL drift kontrolü

**Files:**
- Modify: `council/verifier.py` (tüm CLOB bloğu kaldırılır, sadece HL drift kalır)
- Modify: `tests/test_verifier.py` (CLOB kontrolü testleri kaldırılır, HL drift testi güncellenir)

**Bağlam:** Mevcut `verifier.py` 3 şey yapıyor: (1) HL drift kontrolü, (2) CLOB fiyat çekimi, (3) edge yeniden hesabı. Scout artık CLOB fiyatını kullandığı için (2) ve (3) gereksiz. Sadece (1) kalacak. Verifier'ın return formatı aynı kalacak — downstream modüller (redteam, risk) bu formatı bekliyor.

- [ ] **Step 1: Failing test yaz**

`tests/test_verifier.py` sonuna ekle:

```python
@pytest.mark.asyncio
async def test_verify_passes_through_scout_clob_prices():
    """Verifier artık CLOB çağrısı yapmaz, scout'un best_ask/best_bid'ini geçirir."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.55, best_bid=0.45,  # scout'un CLOB fiyatları
        fair_value=0.62, seconds_remaining=300.0,
        cur_price=105_000.0,
    )
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_100.0):
        result = await verify(finding)
    assert result["pass"] is True
    assert abs(result["fresh_best_ask"] - 0.55) < 1e-6, "Scout'un CLOB fiyatı geçirilmeli"
    assert abs(result["fresh_best_bid"] - 0.45) < 1e-6
```

```bash
pytest tests/test_verifier.py::test_verify_passes_through_scout_clob_prices -v 2>&1 | tail -5
```
Expected: FAIL (verifier hâlâ CLOB çağırıyor, test beklentisi karşılanmıyor)

- [ ] **Step 2: `council/verifier.py`'yi yeniden yaz**

Tüm dosyayı şu içerikle değiştir:

```python
"""
council/verifier.py — KATMAN 2: HL Drift Kontrolü.

Scout zaten CLOB gerçek zamanlı fiyatıyla edge hesapladı.
Verifier sadece şunu kontrol eder: Scout'tan bu yana HL fiyatı >%2 oynadı mı?
Oynadıysa → fair value bozulur → veto.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import current_price
import config

PRICE_DRIFT_HALT_PCT = 2.0  # HL fiyatı Scout'tan bu yana >%2 farklıysa → HALT


async def verify(finding: dict) -> dict:
    """
    HL drift kontrolü. Scout'un CLOB fiyatlarını pass-through eder.

    Returns:
        {pass, reason, halt, fresh_cur_price, fresh_best_ask, fresh_best_bid,
         fresh_fair, fresh_edge, fresh_seconds, hl_drift_pct, pm_drift}
    """
    asset     = finding["asset"]
    scout_cur = finding["cur_price"]

    try:
        fresh_cur = await current_price(asset)
    except Exception as e:
        return _result(False, "fetch_error", False, extra={"error": str(e)})

    hl_drift = abs(fresh_cur - scout_cur) / scout_cur * 100
    if hl_drift > PRICE_DRIFT_HALT_PCT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    # Scout CLOB fiyatlarını zaten kullandı — pass-through
    return _result(True, "ok", False,
                   fresh_cur=fresh_cur,
                   fresh_ask=finding["best_ask"],
                   fresh_bid=finding["best_bid"],
                   fresh_seconds=finding["seconds_remaining"],
                   fresh_fair=finding["fair_value"],
                   fresh_edge=finding["edge"],
                   hl_drift_pct=hl_drift)


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
    print("VERIFIER — Scout bulgularında HL drift kontrolü")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu gelmedi.")
        return
    for f in findings:
        r = await verify(f)
        icon = "PASS" if r["pass"] else f"FAIL [{r['reason']}]"
        halt = " *** HALT ***" if r["halt"] else ""
        print(f"\n{f['question'][:55]}")
        print(f"  Scout CLOB ask : {f['best_ask']:.3f}  edge:{f['edge']:+.3f}")
        print(f"  HL drift       : {r['hl_drift_pct']:.4f}%")
        print(f"  Sonuç          : {icon}{halt}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 3: Yeni test yeşil mi?**

```bash
pytest tests/test_verifier.py::test_verify_passes_through_scout_clob_prices -v 2>&1 | tail -5
```
Expected: `1 passed`

- [ ] **Step 4: Mevcut verifier testlerini güncelle**

```bash
pytest tests/test_verifier.py -v 2>&1 | tail -30
```

Artık CLOB mock'u gerektiren testler (`get_clob_price` patch'i olan testler) başarısız olacak çünkü verifier artık `get_clob_price` import etmiyor.

Bunları güncelle:
- `get_clob_price` patch'ini kaldır
- `fetch_by_slug` patch'ini kaldır (verifier artık `fetch_by_slug` kullanmıyor)
- `fair_yes` patch'ini kaldır (verifier artık `fair_yes` hesaplamıyor)
- Assertion'ları güncelle: `fresh_best_ask` artık `finding["best_ask"]` değerine eşit olmalı

Kaldırılacak testler (artık geçersiz — CLOB verifier mantığını test ediyorlar):
- `test_verify_edge_gone_when_clob_eliminates_edge`
- `test_verify_edge_gone_when_no_clob_liquidity`
- `test_verify_no_halt_on_large_clob_vs_market_api_drift`
- `test_verify_no_action_uses_no_token_id`
- `test_verify_yes_action_uses_yes_token_id`
- `test_verify_uses_clob_price_for_edge_not_market_api`

Kalacak/güncellenen testler:
- `test_verify_hl_drift_triggers_halt` → `get_clob_price` patch kaldır, sadece HL drift testi
- `test_verify_expired_soft_fail` → artık geçersiz (verifier seconds kontrolü yapmıyor) → kaldır
- `test_verify_fetch_error` → `current_price` exception → FAIL "fetch_error" → kalır

- [ ] **Step 5: Tüm verifier testleri yeşil**

```bash
pytest tests/test_verifier.py -v 2>&1 | tail -15
```
Expected: all passed (eski CLOB testleri kaldırıldı, yenileri geçiyor)

- [ ] **Step 6: Full test suite**

```bash
pytest tests/ --tb=short -q 2>&1 | tail -5
```
Expected: ≥300 passed, 0 failed

- [ ] **Step 7: Commit**

```bash
git add council/verifier.py tests/test_verifier.py
git commit -m "refactor(verifier): CLOB kontrolü kaldırıldı, sadece HL drift kalır

Scout artık CLOB fiyatıyla edge hesaplıyor.
Verifier sadece HL fiyat drift'ini kontrol eder (1 API çağrısı).
Council gecikmesi ~10-20s → ~2-4s'ye düştü."
```

---

### Task 3: Temizlik + Push + Restart

**Files:**
- Modify: `main_loop.py` (geçici debug print'leri kaldır)

- [ ] **Step 1: Debug print'leri kaldır**

`main_loop.py` içindeki geçici satırları kaldır:

```python
# Bu satırları SİL:
print("[bot] bankroll sorgulanıyor...")
print(f"[bot] bankroll={starting_bankroll:.2f}")
print("[bot] notify_restart...")
print("[bot] döngü başlıyor...")
print(f"[scan] {len(findings)} bulgu, {len(open_positions)}/{config.MAX_OPEN_POSITIONS} açık pozisyon")
print(f"[council] VETO verifier | ...")  # _run_council içindeki debug print
```

- [ ] **Step 2: Full suite son kontrol**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/ -q --tb=short 2>&1 | tail -5
```
Expected: ≥300 passed, 0 failed

- [ ] **Step 3: Commit + push**

```bash
git add main_loop.py
git commit -m "chore: debug print'leri temizle"
git push origin master
```

- [ ] **Step 4: Restart**

```bash
./restart.sh
```

- [ ] **Step 5: İlk scan'i doğrula**

```bash
until grep -q "\[scan\]" logs/main_loop.log; do sleep 3; done && grep "\[scan\]\|\[clob\].*FILLED" logs/main_loop.log | tail -20
```

Expected: `[scan] N bulgu` (N > 0) ve `[clob] ... FILLED` (trade açıldı)
