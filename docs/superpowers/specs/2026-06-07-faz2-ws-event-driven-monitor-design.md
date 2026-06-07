# Faz 2 — WS Event-Driven Position Monitor: Tasarım Spesifikasyonu

**Tarih:** 2026-06-07  
**Katılımcılar:** Claude (mimar), Codex (reviewer), Gemini (reviewer), Hasan (karar verici)  
**Durum:** ONAYLANDI

---

## Problem

`main_loop._monitor_positions` her 7 saniyede bir REST poll yapıyor. `ws_prices.py` zaten WS fiyat akışını cache'liyor ama monitor bu akışı dinlemiyor. Sonuç: stop kararı ~7s geç, fill ~-37.9% (trigger ~-30%). WebSocket event-driven yapıya geçince `trigger_to_fill_secs` 7s → <1s hedefleniyor, avg loss $0.49 → $0.38 beklentisi.

---

## Kabul Edilen Tasarım: Yaklaşım A1

**Event wake-up + cached context + full check_exit**

### 6 Kural (Codex/Gemini/Claude/Hasan konsensüsü)

1. **Full event wake-up:** WS fiyat tick'i gelince `asyncio.Event` ateşlenir, monitor uyanır, tüm açık pozisyonlar `check_exit()` ile taranır (MAE, MFE, stop-loss, profit-target).
2. **Event path'te REST yok:** `hl_price` ve `seconds_remaining` cached değerler kullanılır. WS event path'e sıfır REST gecikmesi girer.
3. **7s heartbeat:** REST döngüsü cache tazelemek ve fallback için arka planda çalışmaya devam eder.
4. **Profit confirm zaman kapısı:** `PROFIT_CONFIRM_CYCLES=2` korunur, **ek olarak** `MIN_PROFIT_CONFIRM_SECS=3` minimum zaman kapısı eklenir. WS hızında 2 cycle ≈ 150ms olabilir — bu artık anti-glitch değil. İlk confirm ile son confirm arasında en az 3s geçmeli.
5. **Double-close koruması:** `pos["_closing"] = True` sell başlamadan önce set edilir. Event path `_closing` olan pozisyonları skip eder.
6. **FAK fail reset:** `sell_position()` None döndürürse `pos["_closing"] = False` reset edilir, bir sonraki döngüde tekrar denenir.

---

## Neden A2 Reddedildi

"Profit-target ve max_hold heartbeat'te kalsın" yaklaşımı: binary option'da profit spike 1-3 saniye yaşayabilir. Sistemin stop-loss'unu hızlandırıp profit yakalamayı kör bırakmak asimetrik risk yaratır.

---

## Etkilenen Modüller

### `data/ws_prices.py`

```python
_price_event: asyncio.Event | None = None

def get_price_event() -> asyncio.Event:
    """Monitor'un dinleyeceği global price event."""
    global _price_event
    if _price_event is None:
        _price_event = asyncio.Event()
    return _price_event
```

`_update_cache()` sonuna eklenir:
```python
if _price_event is not None:
    _price_event.set()
```

### `position/manager.py`

`check_exit()` profit confirm bloğu revize:

```python
MIN_PROFIT_CONFIRM_SECS = 3  # WS hızında cycle-sayısı yeterli değil, zaman kapısı lazım

# profit_ready bloğunda:
if profit_ready and not near_expiry:
    position["_profit_confirm"] = position.get("_profit_confirm", 0) + 1
    position.setdefault("_profit_confirm_first_ts", now.isoformat())
    elapsed = (now - datetime.fromisoformat(position["_profit_confirm_first_ts"])).total_seconds()
    if (position["_profit_confirm"] >= PROFIT_CONFIRM_CYCLES
            and elapsed >= MIN_PROFIT_CONFIRM_SECS):
        return "profit_target_hit"
else:
    position["_profit_confirm"] = 0
    position.pop("_profit_confirm_first_ts", None)  # zaman kapısını da resetle
```

### `main_loop.py`

`_monitor_positions` iki path'li yapıya dönüşür:

```
WS event geldi → event.clear() → cached context ile check_exit (tüm pozisyonlar)
7s timeout     → REST refresh  → cache güncelle + fallback check_exit
```

`_closing` flag yönetimi:

```python
if pos.get("_closing"):
    continue  # zaten satılıyor

pos["_closing"] = True
pm_exit = await sell_position(pos)
if pm_exit is None:
    pos["_closing"] = False  # FAK fail, sonraki döngüde tekrar dene
    continue
# başarılı → zaten open_positions'dan çıkarılır
```

Cache yazımı (REST heartbeat path):
```python
pos["_cached_hl_price"]          = hl_price
pos["_cached_seconds_remaining"] = window["seconds_remaining"]
```

---

## Değişmeyen Şeyler

- `PROFIT_CONFIRM_CYCLES = 2` — değer korunuyor, sadece zaman kapısı ekleniyor
- `DYNAMIC_STOP_LOSS` mantığı — dokunulmaz
- `config.py` guardrail sabitleri — dokunulmaz
- `sell_position()` ve order construction — dokunulmaz
- Strateji parametreleri — dokunulmaz

---

## Beklenen Metrik İyileşmesi

| Metrik | Faz 1 (polling) | Faz 2 (event-driven) |
|--------|-----------------|----------------------|
| `trigger_to_fill_secs` | ~7s | <1s hedef |
| `trigger_fill_gap_pct` | ~-13% | ~-3% beklenti |
| avg loss | ~$0.49 | ~$0.38-0.40 beklenti |
| Breakeven WR | %58.3 | ~%52 hedef |

---

## Test Kapsamı (TDD)

Her değişiklik için önce failing test yazılır:

1. `test_ws_prices.py` — `get_price_event()` + `_update_cache` event'i set ediyor
2. `test_position.py` — profit confirm zaman kapısı (cycles ✓ ama <3s → pass etme)
3. `test_main_loop.py` — WS event path (REST yok), REST heartbeat path, `_closing` flag, double-close koruması
