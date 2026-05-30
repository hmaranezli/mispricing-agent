# Verifier (Katman 2) — Tasarım Dokümanı

**Tarih:** 2026-05-30  
**Durum:** Onaylandı

---

## Amaç

Scout'un bulduğu mispricing adayını, bağımsız bir API çağrısıyla teyit etmek. Scout ile Verifier arasında geçen 5-15 saniyede fiyatlar değişmiş olabilir. Verifier bunu tespit eder ve iki farklı başarısızlık türünü birbirinden ayırır.

---

## İki Başarısızlık Türü

| Tür | Tanım | Sonuç |
|-----|-------|-------|
| **Soft fail** | Edge geçerliliğini yitirdi (piyasa zaten fiyatlandı, süre doldu) | O market atlanır, sistem devam eder |
| **Hard fail / HALT** | API verisi tutarsız (HL veya PM fiyatı anormal drift) | `HALT_ON_API_MISMATCH` devreye girer, sistem durur |

---

## Re-fetch Edilenler

| Veri | Kaynak | Neden |
|------|--------|-------|
| `cur_price` | Hyperliquid (`current_price`) | Her saniye değişebilir |
| `best_ask / best_bid` | Gamma CLOB (`fetch_by_slug`) | MM'ler günceller |
| `seconds_remaining` | `endDate - now` yeniden hesap | Süre geçiyor |

**Re-fetch edilmeyenler:**
- `ref_price` — geçmiş mum verisi, immutable
- `fair_value` — taze verilerden yeniden hesaplanır

---

## Tolerans Eşikleri

`verifier.py`'de sabit olarak tanımlanır (config.py'e dokunulmaz):

```python
PRICE_DRIFT_HALT_PCT = 2.0   # HL fiyatı >%2 farklıysa → HALT
PM_DRIFT_HALT        = 0.10  # PM bestAsk >0.10 hareket ettiyse → HALT
```

**Gerekçe:**
- BTC 10 saniyede normalde 0.01–0.05% oynar. %2 = ~$1500 anlık kayma → ya API hatası ya flash crash.
- PM'de 0.10 cent kayma → piyasa zaten fiyatlandı ya da market maker çekildi.

---

## Doğrulama Akışı

```
verify(finding: dict) → dict

1. HL cur_price taze çek
2. HL drift > PRICE_DRIFT_HALT_PCT? → HALT (api_mismatch)
3. PM bestAsk/bestBid slug ile taze çek
4. PM drift > PM_DRIFT_HALT? → HALT (api_mismatch)
5. fresh_seconds_remaining < 60? → soft fail (expired)
6. fair_value yeniden hesapla (fair_yes ile)
7. edge yeniden hesapla (action'a göre YES veya NO)
8. fresh_edge < MIN_EDGE_PCT? → soft fail (edge_gone)
9. → PASS (taze verileri döndür)
```

---

## Output Formatı

```python
{
    # Karar
    "pass":   bool,
    "reason": "ok" | "edge_gone" | "expired" | "api_mismatch" | "fetch_error",
    "halt":   bool,   # sadece api_mismatch'te True

    # Taze veriler (sonraki katmanlara iletilir)
    "fresh_cur_price": float,
    "fresh_best_ask":  float,
    "fresh_best_bid":  float,
    "fresh_fair":      float,
    "fresh_edge":      float,
    "fresh_seconds":   float,

    # Log karşılaştırması
    "hl_drift_pct":    float,   # abs(fresh - scout) / scout * 100
    "pm_drift":        float,   # abs(fresh_ask - scout_ask)
}
```

---

## Dosya Değişiklikleri

| Dosya | İşlem | Açıklama |
|-------|--------|----------|
| `council/verifier.py` | **YENİ** | Ana doğrulama mantığı |
| `council/scout.py` | **KÜÇÜK DEĞİŞİKLİK** | `slug` alanı output'a eklenir |
| `tests/test_verifier.py` | **YENİ** | Unit + integration testler |

---

## Test Stratejisi

Gerçek API kullanılır — mock yok (CLAUDE.md kuralı).

- `test_verify_returns_dict_structure()` — çıktı formatı doğru mu?
- `test_verify_pass_on_real_market()` — gerçek Scout bulgusu → PASS veya soft fail
- `test_verify_soft_fail_edge_gone()` — edge=0.00 olan sahte bulgu → edge_gone
- `test_verify_soft_fail_expired()` — seconds_remaining=0 → expired
- `test_verify_halt_on_hl_drift()` — scout_cur_price ile gerçek fiyat arası >2% → api_mismatch
- `test_verify_halt_flag_is_true()` — api_mismatch'te halt=True
- `test_verify_soft_fail_halt_is_false()` — soft fail'de halt=False
