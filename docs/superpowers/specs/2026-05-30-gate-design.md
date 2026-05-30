# Katman 5: Gate — Tasarım Dokümanı

Tarih: 2026-05-30  
Durum: Onaylandı  
Bağlam: 5 katmanlı konseyin son katmanı. Scout→Verifier→RedTeam→Risk geçmiş bulgu için güven skoru hesaplar, insan onayı yönetir, DRY_RUN'da loglar.

---

## Amaç

Gate **karar verir ve uygular.** Diğer 4 katman veto eder; Gate tek "aksiyonu" alan katmandır.

Sorduğu soru: *"Her şey kontrol edildi — şimdi gerçekten giriyor muyuz?"*

---

## Mimari: 2 Katmanlı

```
_confidence_score()   saf fonksiyon — 4 sinyalden 0-100 skor
_gate_decide()        saf fonksiyon — skor < eşik → veto
gate()                async wrapper — log + approval + aksiyon
```

Saf fonksiyonlar API/DB/dosya bağımlılığı olmadan test edilir.
`gate()` DRY_RUN=True ile entegrasyon testinde çalışır.

---

## Güven Skoru Formülü

4 bileşen, ağırlıklı toplam (0-100):

```python
def _confidence_score(redteam: dict, verification: dict) -> float:
    # Edge bileşeni (0-40): MIN_EDGE_PCT(%8)→0, %15+→40
    edge = redteam["fee_adj_edge"]
    edge_s = min(max((edge - 0.08) / 0.07, 0.0), 1.0)

    # Likidite bileşeni (0-30): $500→0, $3000+→30
    liq = redteam["liquidity_usd"]
    liq_s = min(max((liq - 500) / 2500, 0.0), 1.0)

    # Süre bileşeni (0-15): 120s→0, 300s+→15
    secs = verification["fresh_seconds"]
    time_s = min(max((secs - 120) / 180, 0.0), 1.0)

    # Spread bileşeni (0-15): 0.04→0, 0.01+→15
    spread = redteam["spread"]
    spread_s = min(max((0.04 - spread) / 0.03, 0.0), 1.0)

    return round(edge_s * 40 + liq_s * 30 + time_s * 15 + spread_s * 15, 1)
```

### Kalibrasyon

| Senaryo | Edge | Liq | Süre | Spread | Skor | Karar |
|---------|------|-----|------|--------|------|-------|
| Tipik iyi | %12 | $3000 | 400s | 0.02 | ~78 | GEÇER |
| Zayıf | %9 | $800 | 150s | 0.035 | ~14 | VETO |
| Mükemmel | %18+ | $5000+ | 600s+ | 0.01 | ~100 | GEÇER |
| Eşik altı | %10 | $1500 | 200s | 0.03 | ~42 | VETO |

Eşik: `config.CONFIDENCE_THRESHOLD = 75` (değiştirilemez).

---

## Input / Output

```python
async def gate(
    finding:      dict,   # Scout çıktısı
    verification: dict,   # Verifier çıktısı
    redteam:      dict,   # RedTeam çıktısı
    risk_result:  dict,   # Risk çıktısı (position_usd, requires_human_approval)
) -> dict
```

```python
{
    "pass":             bool,
    "confidence_score": float,   # 0-100
    "action_taken":     str,     # "dry_run_logged" | "vetoed" | "approval_timeout"
    "reason":           str,     # veto gerekçesi veya ""
}
```

---

## Akış

```
gate() çağrılır
  ↓
_gate_decide():
  skor hesapla
  skor < CONFIDENCE_THRESHOLD → pass=False, action_taken="vetoed"
  ↓
pass=False → log → dön
  ↓
requires_human_approval?
  DRY_RUN=True  → "onay isterdim" notunu loga ekle, devam et
  DRY_RUN=False → Telegram alert, 5dk bekle
                  timeout → action_taken="approval_timeout", pass=False, dön
  ↓
_log() → logs/dry_run.jsonl satırına yaz
  ↓
action_taken = "dry_run_logged"
pass = True → dön
```

---

## Log Formatı (JSONL)

Dosya: `logs/dry_run.jsonl` — her satır bağımsız bir JSON nesnesi.

```json
{
  "ts": "2026-05-30T10:00:00Z",
  "dry_run": true,
  "pass": true,
  "action": "YES",
  "slug": "btc-up-1h",
  "asset": "BTC",
  "position_usd": 42.0,
  "confidence_score": 77.9,
  "fee_adj_edge": 0.12,
  "liquidity_usd": 3000.0,
  "fresh_seconds": 400,
  "spread": 0.02,
  "action_taken": "dry_run_logged",
  "requires_human_approval": false,
  "reason": ""
}
```

Veto edilen işlemler de loglanır (`pass=false`, `action_taken="vetoed"`). Tüm kararlar kayıtta.

---

## Modül Sabitleri (gate.py içinde)

```python
EDGE_ZERO    = 0.08   # config.MIN_EDGE_PCT ile eşit
EDGE_MAX     = 0.15   # Bu noktada edge skoru maksimum
LIQ_ZERO     = 500    # RedTeam LIQUIDITY_VETO_USD ile eşit
LIQ_MAX      = 3000
TIME_ZERO    = 120    # RedTeam MIN_THESIS_SECS ile eşit
TIME_MAX     = 300
SPREAD_ZERO  = 0.04
SPREAD_MAX   = 0.01
APPROVAL_TIMEOUT_SECS = 300   # 5 dakika
LOG_FILE     = "logs/dry_run.jsonl"
```

---

## Test Stratejisi

| Test | Ne kontrol eder | Tip |
|------|----------------|-----|
| `test_confidence_score_typical_good` | edge=0.12 vb. → skor > 75 | unit |
| `test_confidence_score_weak` | zayıf sinyal → skor < 75 | unit |
| `test_confidence_score_perfect` | tüm max → ~100 | unit |
| `test_confidence_score_clamped` | aşırı değerler → 100'ü geçmez | unit |
| `test_gate_decide_required_fields` | çıktı şeması tam | unit |
| `test_gate_decide_vetoes_below_threshold` | skor < 75 → pass=False | unit |
| `test_gate_decide_passes_above_threshold` | skor ≥ 75 → pass=True | unit |
| `test_gate_dry_run_logged` | DRY_RUN=True → action_taken="dry_run_logged" | async |
| `test_gate_vetoed_no_log_as_order` | veto → action_taken="vetoed" | async |
| `test_gate_approval_flag_dry_run_does_not_block` | requires_human_approval + DRY_RUN → geçer | async |

**Hedef:** 10 test, 0 skip, 0 gerçek API çağrısı.

---

## Bağımlılıklar

- `config.py` — CONFIDENCE_THRESHOLD, DRY_RUN, HUMAN_APPROVAL_USD
- `council/risk.py` — risk_result["requires_human_approval"], risk_result["position_usd"]
- `council/redteam.py` — fee_adj_edge, liquidity_usd, spread
- `council/verifier.py` — fresh_seconds
- Dış bağımlılık: yalnızca `logs/dry_run.jsonl` dosyası (oluşturulmazsa oluşturulur)
- Telegram: DRY_RUN=True iken hiç kullanılmaz

---

## Dosya Yapısı

```
council/gate.py          # Ana modül (~130-160 satır)
tests/test_gate.py       # 10 test (7 sync + 3 async)
logs/dry_run.jsonl       # DRY_RUN çıktısı (git'e eklenmez)
```

---

## Gelecek: DB Entegrasyonu

`_log()` fonksiyonu şu an JSONL'a yazar. İleride DB katmanı hazır olduğunda bu tek fonksiyon değişir, `gate()` değişmez. Interface temiz.
