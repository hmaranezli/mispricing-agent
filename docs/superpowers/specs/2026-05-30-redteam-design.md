# RedTeam (Katman 3) — Tasarım Dokümanı

**Tarih:** 2026-05-30  
**Durum:** Onaylandı

---

## Amaç

Scout + Verifier'dan geçen bulguya karşı şeytan avukatı olmak. "Bu işlemi NEDEN yapmamalıyız?" sorusunu sorar. İkna olursa veto, olmaz ise pass.

---

## Sorumluluk Sınırı

| Katman | Sorusu |
|--------|--------|
| Verifier | Veri tutarlı mı? (API drift, fiyat teyidi) |
| **RedTeam** | **Strateji bu şartlarda çalışır mı? (likidite, fee, zaman, mantık)** |

---

## 6 Kontrol

| # | Kontrol | Tür | Eşik | Kaynak |
|---|---------|-----|------|--------|
| 1 | Bid-ask spread | Veto | > 0.05 | Gamma `spread` |
| 2 | CLOB likidite | Veto | < $500 | Gamma `liquidityClob` |
| 3 | Fee sonrası edge | Veto | < MIN_EDGE_PCT | `takerBaseFee` + fair_value |
| 4 | Kalan süre | Veto | < 120s | Verifier `fresh_seconds` |
| 5 | Edge sağlık kontrolü | Veto | > 0.35 (veri hatası şüphesi) | Verifier `fresh_edge` |
| 6 | 24s hacim | Warning | < $50 | Gamma `volume24hr` |

Warning'ler loglanır, işlemi durdurmaz. Herhangi bir veto → `pass=False`.

---

## Fee Hesabı

Gamma API `takerBaseFee` alanından gerçek fee çekilir.
Birimi implement esnasında doğrulanır (bps veya farklı ölçek) — Polymarket'in %2 dokümanlı fee'si referans alınır.

```
YES alımı:
  fee_adj_edge = fair × (1 − fee) − best_ask

NO alımı:
  fee_adj_edge = (1 − fair) × (1 − fee) − (1 − best_bid)

fee_adj_edge < MIN_EDGE_PCT → veto: edge_killed_by_fee
```

---

## Veri Akışı

RedTeam, Gamma'dan slug ile bağımsız API çağrısı yapar (`fetch_by_slug` — mevcut).  
Scout veya Verifier'a dokunulmaz, ek bağımlılık yok.

**Input:**
```python
finding:      dict  # Scout çıktısı (slug, action, fair_value dahil)
verification: dict  # Verifier çıktısı (fresh_fair, fresh_edge, fresh_seconds dahil)
```

**Output:**
```python
{
    "pass":         bool,
    "vetoes":       list[str],   # boşsa pass=True
    "warnings":     list[str],   # loglanır, bloklamaz
    "fee_adj_edge": float,
    "taker_fee":    float,       # ondalık (örn. 0.02)
    "spread":       float,
    "liquidity_usd": float,
}
```

**Veto kodları:**
- `spread_too_wide`
- `liquidity_insufficient`
- `edge_killed_by_fee`
- `insufficient_time_for_thesis`
- `edge_suspiciously_large`

---

## Eşik Sabitleri (redteam.py içinde)

```python
SPREAD_VETO        = 0.05   # > 5 cent spread
LIQUIDITY_VETO_USD = 500    # < $500 CLOB likiditesi
VOLUME_WARN_USD    = 50     # < $50 günlük hacim (warning)
MIN_THESIS_SECS    = 120    # < 2dk → PM'in yeniden fiyatlanması için yeterli zaman yok
EDGE_SANITY_MAX    = 0.35   # > %35 edge → muhtemelen veri hatası
```

---

## Dosya Değişiklikleri

| Dosya | İşlem |
|-------|--------|
| `council/redteam.py` | **YENİ** |
| `tests/test_redteam.py` | **YENİ** |

Scout, Verifier, config.py'e dokunulmaz.

---

## Test Stratejisi

Gerçek API + sahte finding kombinasyonu — mock yok.

- `test_veto_spread_too_wide()` — spread=0.99 sahte bulgu → spread_too_wide veto
- `test_veto_liquidity_insufficient()` — liquidityClob=0 → liquidity_insufficient
- `test_veto_edge_killed_by_fee()` — fee=0.50 → edge_killed_by_fee
- `test_veto_insufficient_time()` — fresh_seconds=60 → insufficient_time_for_thesis
- `test_veto_edge_suspicious()` — fresh_edge=0.40 → edge_suspiciously_large
- `test_warning_low_volume_no_veto()` — düşük hacim → pass=True ama warnings dolu
- `test_pass_structure()` — tüm alanlar çıktıda var
- `test_real_pipeline()` — Scout → Verifier → RedTeam gerçek API zinciri
