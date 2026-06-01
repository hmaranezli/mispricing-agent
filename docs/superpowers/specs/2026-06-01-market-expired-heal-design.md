# market_expired Heal — Tasarım Dokümanı

**Tarih:** 2026-06-01  
**Durum:** Onaylı

---

## 1. Problem

Polymarket'in resolution API'si, market penceresi kapandıktan 2-5 dakika sonra
`outcomePrices` yayınlıyor. Bot 30s'de bir tarar. Market kapandığı anda:

```
window = None  →  fetch_resolved(slug)  →  API henüz boş  →  market_expired
pm_exit_price = None, realized_pnl = None
open_positions.remove(pos)  ←  artık izlenmiyor, asla retry yok
```

**Etki:** 92 kapanan pozisyonun 31'i (%33) P&L bilinmiyor.
Strateji analizi bu haliyle eksik ve yanıltıcı.

## 2. Root Cause

Tek root cause: `fetch_resolved` ilk çağrıda None dönünce pozisyon
monitoring'den kalıcı olarak çıkarılıyor. Race window ~2dk → ~%33 oranında yakalanıyor.

## 3. Yaklaşım — DB-driven Healing

İki katmanlı çözüm; mekanizma aynı, kullanım yeri farklı:

### Katman A: Retroaktif Script (one-shot)
`analysis/backfill_expired.py` — mevcut 31 null kaydı çalıştırıldığında heal eder.
Sonuç: strateji analizi bugün yapılabilir.

### Katman B: Yapısal Fix (kalıcı)
`_heal_pending_resolutions(conn)` — her scan'in sonunda çalışır.
`status='closed' AND pm_exit_price IS NULL` kayıtları sorgular.
Resolve edilmişse patch'ler; hâlâ boşsa geçer (retry, limit=3/scan).

## 4. Dosya Haritası

| Dosya | İşlem | Değişiklik |
|-------|--------|-----------|
| `db/logger.py` | Güncelle | `patch_position_resolution()` yeni fonksiyon |
| `analysis/backfill_expired.py` | Yeni | One-shot retroaktif heal script |
| `main_loop.py` | Güncelle | `_heal_pending_resolutions()` + main loop'a çağrı |
| `tests/test_db.py` | Güncelle | patch_position_resolution testi |
| `tests/test_main_loop.py` | Güncelle | heal fonksiyonu testi (2 test) |

## 5. Arayüzler

### `patch_position_resolution(conn, position_id, pm_exit_price, realized_pnl, exit_reason)`
```python
# db/logger.py
# Kapanmış pozisyonun exit verisini DB'ye yazar.
# exit_reason: 'market_resolved_late'
```

### `_heal_pending_resolutions(conn, closed_today, limit=3)`
```python
# main_loop.py — async
# status='closed' AND pm_exit_price IS NULL olan kayıtları sorgular.
# Her biri için fetch_resolved çağırır.
# Resolve edilmişse: patch_position_resolution + closed_today güncelle.
# limit: API baskısını önlemek için scan başına max işlem.
```

### `backfill_expired.py`
```python
# Standalone async script.
# python analysis/backfill_expired.py
# Çıktı: "X recovered, Y still null (canceled markets?)"
```

## 6. exit_reason Sözleşmesi

| Değer | Anlam |
|-------|-------|
| `market_resolved` | Gerçek zamanlı — fetch_resolved ilk çağrıda döndü |
| `market_resolved_late` | Gecikmeli — heal mekanizması ile düzeltildi |
| `market_expired` | Asla resolve olamadı (iptal market, çok eski slug, API arıza) |

## 7. P&L Formülü (değişmiyor)

```python
realized_pnl = (pm_exit_price - pm_entry_price) / pm_entry_price * position_usd
```

YES pozisyon, YES resolve → exit=1.0, pozitif P&L  
YES pozisyon, NO resolve → exit=0.0, negatif P&L (total loss)  
NO pozisyon: exit = no_exit (= 1 - yes_exit)

## 8. Test Planı

| # | Test | Açıklama |
|---|------|---------|
| 1 | `test_patch_position_resolution_writes_db` | patch sonrası DB'de doğru değerler |
| 2 | `test_heal_fixes_null_pnl_when_api_returns` | heal → fetch_resolved mock → DB patch |
| 3 | `test_heal_skips_when_api_still_none` | fetch_resolved hâlâ None → kayıt dokunulmaz |
| 4 | `test_heal_respects_limit` | 5 null kayıt varsa limit=3 → 3 işlenir |

## 9. Sıradaki

Bu sprint bittikten sonra → `python analysis/backfill_expired.py` çalıştır → strateji analizi.
