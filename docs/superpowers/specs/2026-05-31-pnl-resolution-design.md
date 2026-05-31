# P&L Resolution Design

**Tarih:** 2026-05-31  
**Konu:** market_expired kapanışlarda Polymarket resolution sonucunu çekip P&L hesaplama

## Problem

Pozisyon `market_expired` ile kapandığında `pm_exit_price = NULL`. Kazandık mı kaybettik mi bilinmiyor. Dry-run'ı değerlendirmek için P&L şart.

## API Kanıtı

`GET /markets?slug={slug}&closed=true` → kapanmış marketi döndürür:
- `outcomePrices: ["1", "0"]` — Up kazandı, Down kaybetti  
- `outcomes: ["Up", "Down"]`  
- `eventMetadata.finalPrice` ve `priceToBeat` — gerçek fiyatlar

## Tasarım

### 1. `data/shortterm.py` — `fetch_resolved(slug)`

```python
async def fetch_resolved(slug: str) -> dict | None:
    """Kapanmış market için resolution fiyatlarını döndürür."""
    # GET /markets?slug={slug}&closed=true
    # Returns: {"yes_exit": float, "no_exit": float} veya None
```

- `outcomePrices[0]` = YES (Up) exit fiyatı (0.0 veya 1.0)
- `outcomePrices[1]` = NO (Down) exit fiyatı (0.0 veya 1.0)
- Bulunamazsa None

### 2. `main_loop._monitor_positions` güncelleme

`window is None` olduğunda:
1. `fetch_resolved(slug)` çağır
2. Bulunursa: `action`'a göre `pm_exit_price` seç (YES→yes_exit, NO→no_exit)
3. `close_position(pos, "market_resolved", pm_exit_price=pm_exit_price)`
4. Bulunamazsa: eski davranış (`market_expired`, pm_exit_price=None)

### 3. P&L hesabı

```python
pnl_usd = (pm_exit_price - pm_entry_price) / pm_entry_price * position_usd
# Örnek: (0.0 - 0.31) / 0.31 * 50 = -$50.00
```

### 4. `monitor/notifier.notify_close` güncelleme

P&L biliniyorsa mesaja ekle:
```
KAPANDI ETH NO
Sebep: market_resolved
P&L: -$50.00 ❌   ← kaybettik
# veya:
P&L: +$111.29 ✅  ← kazandık
```

P&L bilinmiyorsa (None): mevcut format (sebep yeterli).

## Değişmeyen Şeyler

- DB schema değişmez — `pm_exit_price` sütunu zaten var
- `close_position()` değişmez — zaten `pm_exit_price` parametresi var
- `log_position_close()` değişmez

## Test Stratejisi

- `test_fetch_resolved_returns_yes_no_prices` — mock API, outcomePrices parse
- `test_fetch_resolved_returns_none_for_active` — aktif market → None
- `test_monitor_closes_with_resolution_price` — fetch_resolved mock → pm_exit_price dolu
- `test_notify_close_shows_pnl_when_known` — P&L mesaj formatı
