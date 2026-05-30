# execution/ Tasarım Dokümanı

**Tarih:** 2026-05-30  
**Kapsam:** `execution/executor.py` + `tests/test_executor.py`  
**Önceki katman:** Gate (Katman 5) — onay verir  
**Sonraki katman:** position/ — açık pozisyonu izler

---

## 1. Amaç

Gate "geç" dediğinde executor devreye girer. Pre-execution guard'ları sıradan geçirir; DRY_RUN modunda gerçek order göndermez, JSONL'a "şunu yapardım" yazar ve position/ için gereken pozisyon kaydını döndürür.

---

## 2. Arayüz

```python
# execution/executor.py

async def execute(
    finding:        dict,       # scout._process_market() çıktısı
    gate_result:    dict,       # gate.gate() çıktısı
    risk_result:    dict,       # risk.evaluate() çıktısı
    open_positions: list[dict]  # şu an açık pozisyonlar (position/ tutar)
) -> dict | None
```

`None` döndüğünde pozisyon açılmamıştır; çağıran JSONL kaydına bakar.

---

## 3. Finding Yapısı (scout çıktısı — referans)

```python
{
    "question":          str,   # market soru metni
    "asset":             str,   # "BTC" | "ETH"
    "action":            str,   # "YES" | "NO" — hangi token alınıyor
    "fair_value":        float, # Black-Scholes fair value (0-1, YES bazlı)
    "ref_price":         float, # HL fiyatı (market start_ms'inde)
    "cur_price":         float, # HL anlık fiyatı
    "best_ask":          float, # PM'de YES token ask fiyatı
    "best_bid":          float, # PM'de YES token bid fiyatı
    "seconds_remaining": int,   # market kapanışına kalan saniye
    "edge":              float,
    "slug":              str,   # Polymarket market slug
    "neg_risk":          bool,
}
```

---

## 4. Guard Sırası

Aşağıdaki sırayla kontrol edilir; ilk başarısızlıkta `None` döner ve log yazılır:

| # | Koşul | Neden |
|---|-------|-------|
| 1 | `gate_result["pass"] != True` | Gate veto etti, açma |
| 2 | `len(open_positions) >= config.MAX_OPEN_POSITIONS` | Pozisyon tavanı doldu |
| 3 | `config.DRY_RUN == True` | Gerçek order gitmez; log yaz, kayıt döndür |

> Guard 3 her zaman tetiklenir (DRY_RUN=True zorunlu). Gerçek CLOB entegrasyonu `DRY_RUN=False` dalı — bu aşamanın kapsamı dışı.

---

## 5. Giriş Fiyatı Hesabı

```
action == "YES"  →  pm_entry_price = best_ask
action == "NO"   →  pm_entry_price = 1 - best_bid  (NO token maliyeti)
```

---

## 6. Pozisyon Kaydı (dönüş değeri)

```python
{
    "position_id":       str,   # uuid4 — benzersiz tanımlayıcı
    "asset":             str,   # finding["asset"]
    "action":            str,   # finding["action"] — "YES" | "NO"
    "slug":              str,   # finding["slug"]
    "pm_entry_price":    float, # yukarıdaki formülle
    "fair_value":        float, # finding["fair_value"]
    "ref_price":         float, # finding["ref_price"]
    "position_usd":      float, # risk_result["position_usd"]
    "kelly_f":           float, # risk_result["kelly_f"]
    "confidence_score":  float, # gate_result["confidence_score"]
    "seconds_remaining": int,   # finding["seconds_remaining"]
    "opened_at":         str,   # UTC ISO 8601
    "status":            str,   # "open"
    "dry_run":           bool,  # config.DRY_RUN
    "exit_reason":       None,  # position/ doldurur
    "closed_at":         None,  # position/ doldurur
}
```

---

## 7. JSONL Log

`logs/dry_run.jsonl` — gate ile aynı dosya, `layer` alanıyla ayrışır.

**Pozisyon açılınca:**
```json
{
  "ts": "2026-05-30T12:00:00Z",
  "layer": "execution",
  "event": "position_opened",
  "position_id": "3f2a...",
  "asset": "BTC",
  "action": "YES",
  "slug": "btc-up-1hr-...",
  "pm_entry_price": 0.35,
  "fair_value": 0.55,
  "position_usd": 25.0,
  "confidence_score": 82.5,
  "dry_run": true
}
```

**Guard başarısız olunca:**
```json
{
  "ts": "...",
  "layer": "execution",
  "event": "position_skipped",
  "reason": "max_open_positions",
  "dry_run": true
}
```

---

## 8. Test Planı (8 test)

| # | Test | Beklenti |
|---|------|----------|
| 1 | `gate_result["pass"] = False` | `None` döner, JSONL'da `position_skipped` |
| 2 | 5 açık pozisyon varken çağrı | `None` döner, JSONL'da `position_skipped` |
| 3 | Guard'lar geçince (DRY_RUN) | JSONL'da `position_opened` yazılır |
| 4 | JSONL kaydında tüm alanlar var | alan listesi tam |
| 5 | Dönüş değeri pozisyon kaydı | tüm alanlar mevcut, `status="open"` |
| 6 | `position_id` geçerli UUID4 | uuid.UUID(position_id).version == 4 |
| 7 | `opened_at` UTC ISO timestamp | datetime.fromisoformat() hata vermez |
| 8 | İki ardışık çağrı | farklı `position_id` |

---

## 9. Kapsam Dışı

- Gerçek Polymarket CLOB API order gönderimi (`DRY_RUN=False` dalı)
- `HUMAN_APPROVAL_USD` kontrolü — Gate zaten halleder
- PostgreSQL logging — db/ aşamasında eklenir

---

## 10. Bağımlılıklar

```
config.py          (DRY_RUN, MAX_OPEN_POSITIONS)
uuid               (standart kütüphane)
datetime           (standart kütüphane)
json, pathlib      (JSONL yazımı — gate pattern'i)
```

Dışa bağımlılık yok.
