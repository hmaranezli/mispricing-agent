# Shadow Stop & Paper Position Tracker — Tasarım Dokümanı

> **Durum:** TASARIM. Kod/migration/restart YOK. Canlı entry/exit/stop/target/MIN_EDGE değişmez. `NEW_ENTRIES_ENABLED=False` korunur.
>
> **Tarih:** 2026-06-08 · İlgili commit'ler: `6041fbf` (air-pocket shadow Faz A), `9ed4152` (kill-switch)

## 0. Problem & Bağlam

Stop counterfactual analizi gösterdi: mevcut -25% decaying stop, 15m up/down marketlerin gamma-gürültüsünde kârlı sinyalleri kesiyor (hold-to-expiry +$1.75 vs gerçek stop -$4.45). Ama 13-trade örneklemi overfit riski taşıyor; canlı stop değişikliği için daha çok veri gerek.

**Kör nokta (kritik):** `NEW_ENTRIES_ENABLED=False` + açık pozisyon 0 olduğu için:
- Yeni live pozisyon açılmıyor → yeni `stop_loss_hit` yok → `air_pocket_shadow` tablosu **veri üretmiyor**.
- Yani salt "live stop bekleme" stratejisi ölü. Faz B kararı için gereken 20-30 stop event **asla gelmeyecek**.

**Çözüm:** Council'dan geçen ama `entry_disabled` ile execute edilmeyen adaylardan **paper position** üret. Gerçek para yok; PM fiyat path'i, MFE/MAE, stop event, air-pocket shadow event üretir. Bu, tüm shadow modellerini (current/conservative/balanced/MFE-breakeven) besleyen veri musluğudur.

---

## GÖREV 1 — MFE Breakeven Tracker Tasarımı

### mfe_peak izleme

Her pozisyon (paper veya live) için kalıcı state:
```
pos["_mfe_peak"]      = max(pos.get("_mfe_peak", 0.0), current_unrealized_pct)
pos["_mae_trough"]    = min(pos.get("_mae_trough", 0.0), current_unrealized_pct)
pos["_breakeven_armed"] = bool
```
`current_unrealized_pct = (pm_price - entry) / entry` (action yönüne göre işaretli; NO için aşağıda artefakt notu).

Not: `positions` tablosunda `mae_pct`/`mfe_pct` zaten var ve `check_exit` in-memory izliyor. Paper tracker aynı mekanizmayı kullanır.

### Breakeven armed

```
if mfe_peak >= MFE_ARM_THRESHOLD (öneri: 0.15):
    pos["_breakeven_armed"] = True   # bir kez armed, geri dönmez
```

### Breakeven buffer = -3% mantıklı mı?

**Evet, ama nüanslı.** -3% tolerans, +15% görmüş bir pozisyonun küçük geri çekilmede değil, gerçek dönüşte çıkmasını sağlar. Gerekçe:
- 13-trade örneğinde recovered+saved trade'ler +15~26% MFE gördü, sonra çoğu -25%'e düştü. -3% breakeven, +15% kârın çoğunu korurken küçük gürültüye nefes verir.
- **Risk:** Çok sıkı buffer (0%) gürültüde tetiklenir; çok gevşek (-10%) kârı geri verir. -3% orta yol — ama bu **shadow ile doğrulanmalı**, sabit gerçek değil.

### Karar matrisi: EXIT / HOLD / CATASTROPHE_EXIT

```
mfe_breakeven_decide(pos, dd, mae, secs):
    # dd = current drawdown/profit pct (işaretli)
    if elapsed < MIN_HOLD_SECS (15): return HOLD, "min_hold"

    # 1. Felaket önceliği (her durumda)
    if mae < CATASTROPHE_MAE (-0.45): return CATASTROPHE_EXIT, "catastrophe"

    # 2. Expiry yakınlığı → gamma collapse, dökme
    if secs < GAMMA_HOLD_SECS (90):  return HOLD, "gamma_proximity"

    # 3. Breakeven armed ise: entry altına dönerse çık
    if pos["_breakeven_armed"]:
        if dd <= BREAKEVEN_BUFFER (-0.03): return EXIT, "mfe_breakeven_stop"
        return HOLD, "breakeven_watch"

    # 4. Armed değil: sadece felaket floor korur (gürültüye tolerans)
    if dd <= WIDE_FLOOR (-0.35): return EXIT, "wide_floor"
    return HOLD, "noise_tolerance"
```

### Edge cases

| Durum | Davranış |
|-------|----------|
| **Düşük likidite** | Paper'da depth-walk fill estimate; gerçek fill bilinemez → `data_quality="estimated"` |
| **Expiry yakınlığı** | `secs < GAMMA_HOLD_SECS` → HOLD (binary collapse başladı, dökme) |
| **Missing price** | PM fiyat None → o cycle skip, karar verme (mevcut `continue` pattern) |
| **Stale price** | WS cache `STALE_SECS`(15) aşıldıysa REST fallback; ikisi de yoksa skip |
| **NO trade fiyat artefaktı** | `dd` hesabı NO token bid'inden (1-yes_ask değil); complement yalnız fallback. **slippage_pct artefaktı (bkz teşhis) burada tekrarlanmamalı** — NO için NO-token gerçek fiyatı kullan |

---

## GÖREV 2 — Shadow Stop Matrix Tasarımı

Her stop-eligible an için 4 model paralel "ne yapardı" hesaplar. Gerçek karar (live'da) yalnızca `current`; diğerleri gözlem.

| Model | Inputlar | Action | Reason |
|-------|----------|--------|--------|
| **current** | dd, stop_curve(elapsed) | HOLD/EXIT | mevcut canlı mantık aynası |
| **conservative** | dd, hl_drift, elapsed | HOLD/EXIT | erken nefes; sinyal bozulursa (drift>%0.3 ters) çık; yoksa -35% floor |
| **balanced** | dd, hl_drift, frac_elapsed | HOLD/EXIT | stop = lerp(-0.40,-0.20,frac); sinyal bozulursa hızlı çık |
| **mfe_breakeven** | dd, mfe_peak, mae, secs | HOLD/EXIT/CATASTROPHE_EXIT | GÖREV 1 matrisi |

### would_pnl / would_exit_price / would_exit_reason

```
# Bir model EXIT derse, o anki paper exit fiyatı:
would_exit_price  = depth_walk_estimate(book, shares)   # gerçekçi, mid DEĞİL
would_exit_reason = model.reason
would_pnl         = (would_exit_price - entry)/entry * position_usd_paper

# Model HOLD derse pozisyon açık kalır; bir sonraki cycle yeniden değerlendirilir.
# Hiç EXIT etmezse → resolve'da kapanır (backfill).
```

### Resolve backfill

```
# Market kapanınca (fetch_resolved):
resolve_exit = yes_exit if action==YES else no_exit
for model in models:
    if model hiç EXIT etmediyse:
        would_exit_price  = resolve_exit
        would_exit_reason = "held_to_resolve"
        would_pnl         = (resolve_exit - entry)/entry * pos_usd
# shadow_model_pnl tablosuna her model için bir satır.
```

---

## GÖREV 3 — Paper/Shadow Position Tracker Tasarımı

### Tetikleme

`_scan_and_execute` içinde council `pass` ama `NEW_ENTRIES_ENABLED=False` → şu an sadece `[entry_disabled]` loglanıyor. **Buraya** paper position açma eklenir (yalnızca shadow tablolarına; live `positions`'a ASLA dokunmaz).

### Paper entry price — KRİTİK

**Mid KULLANMA (over-optimistic).** Öncelik sırası:
1. **depth-walk estimated fill** (en gerçekçi): `get_book` ask tarafı, `shares` kadar yürü, ağırlıklı ort fiyat. `depth_enricher` pattern'i hazır.
2. **ask + taker_buffer** (fallback): `best_ask + PRICE_PREMIUM(0.01)` — execute()'un gerçek `worst_price` mantığıyla simetrik.
3. mid → **kullanılmaz** (varsayılan değil).

Bu, paper entry'nin gerçek FAK fill'ine yakın olmasını sağlar; paper P&L'i şişirmez.

### Veri üretimi

Paper position, live ile **aynı `_monitor_positions` fiyat altyapısını** kullanır (WS/REST), ama:
- `sell_position()` ÇAĞRILMAZ (gerçek order yok).
- `check_exit()` çağrılır (saf fonksiyon) → exit_reason.
- MFE/MAE/stop event/air-pocket shadow event üretir (sanal fill ile).
- Stop "tetiklendiğinde" sanal exit = depth-walk estimate → `shadow_stop_events` + `air_pocket_shadow` beslenir.

### Confidence / data_quality etiketleme

| Alan | Değer |
|------|-------|
| `cohort` | `"paper"` (live'dan ayrı) |
| `confidence_level` | `"low"` (paper, gerçek fill yok) |
| `data_quality` | `"estimated_fill"` / `"resolve_exact"` |
| `is_paper` | `1` |

### Live ile karışma önlemi

- Paper sonuçları **ayrı tablolarda** (`shadow_positions`, `shadow_stop_events`, `shadow_model_pnl`).
- Live P&L raporları `positions WHERE dry_run=0` kullanmaya devam eder — paper hiç görünmez.
- Rapor katmanında paper cohort **açıkça** "PAPER (low confidence)" etiketiyle ayrılır.
- **Asla** paper P&L'i live KPI'a eklenmez.

### Güven uyarısı

Paper sonuçları live ile aynı güvende **değildir**: gerçek fill slippage'ı, FAK kill, air-pocket yok (tahmin var). Paper, **model sıralaması** ve **yön** için kullanılır — mutlak P&L için değil. Faz B kararı paper + sınırlı live confirmation ister.

---

## GÖREV 4 — DB Schema Tasarımı (öneri, migration YOK)

```sql
-- Paper pozisyonlar (live positions'tan tamamen ayrı)
CREATE TABLE shadow_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, ts_open TEXT, slug TEXT, asset TEXT, action TEXT,
    entry_price_estimated REAL,      -- depth-walk veya ask+buffer
    entry_method TEXT,               -- depth_walk | ask_buffer
    position_usd_paper REAL, shares_paper REAL,
    fair_value REAL, edge REAL, ref_price REAL, entry_hl_price REAL,
    status TEXT DEFAULT 'open',      -- open | closed_paper
    ts_close TEXT, pm_exit_estimated REAL, resolve_exit REAL,
    mae_pct REAL, mfe_pct REAL, mfe_peak REAL,
    cohort TEXT DEFAULT 'paper', confidence_level TEXT DEFAULT 'low',
    data_quality TEXT, is_paper INTEGER DEFAULT 1, created_at TEXT
);

-- Her stop-eligible anda 4 modelin kararı
CREATE TABLE shadow_stop_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, ts TEXT, slug TEXT, asset TEXT, action TEXT,
    seconds_remaining REAL, pm_price REAL, drawdown_pct REAL,
    hl_drift_pct REAL, mae_pct REAL, mfe_pct REAL, mfe_peak REAL,
    current_action TEXT, conservative_action TEXT,
    balanced_action TEXT, mfe_breakeven_action TEXT,
    triggering_model TEXT, decision_reason TEXT, created_at TEXT
);

-- Resolve sonrası her model için kapanış P&L'i
CREATE TABLE shadow_model_pnl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, model TEXT,        -- current|conservative|balanced|mfe_breakeven
    would_exit_price REAL, would_exit_reason TEXT,
    would_exit_ts TEXT, would_pnl REAL,
    resolve_exit REAL, cohort TEXT DEFAULT 'paper', created_at TEXT
);

-- (opsiyonel) paper entry anı snapshot — entry estimate doğruluğu denetimi
CREATE TABLE paper_entry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, ts TEXT, slug TEXT, asset TEXT, action TEXT,
    best_ask REAL, depth_walk_price REAL, ask_buffer_price REAL,
    chosen_price REAL, chosen_method TEXT, book_levels INTEGER, created_at TEXT
);
```

`air_pocket_shadow` tablosu zaten var (commit `6041fbf`); paper stop event'leri `paper_id` ile onu da besler (mevcut şemaya `is_paper` kolonu eklenebilir — gelecekte).

---

## GÖREV 5 — Öncelik Önerisi

### Öneri: **B → C (Paper/Shadow Position Tracker, içinde MFE-breakeven model)**

**Sıralama gerekçesi:**

1. **B zorunlu önkoşul.** Entry kapalı + 0 açık pozisyon → live stop event akmıyor. C/D'nin hiçbiri veri olmadan çalışamaz. Paper tracker veri musluğunu açar — bu olmadan diğer her şey aç kalır.
2. **C, B'nin içinde yaşar.** MFE-breakeven bir model; paper tracker'ın shadow_stop_events matrisindeki 4 modelden biri. Ayrı kodlanmaz, B ile birlikte gelir.
3. **A bu doküman = tamamlandı.**
4. **D (pasif bekleme) reddedilir** — veri üretmez, sadece zaman kaybı; kör nokta nedeniyle hiçbir zaman tetiklenmeyecek live stop'u bekler.

**Somut sıradaki kodlama adımı (onay sonrası, TDD):**
1. `shadow_positions` + `shadow_stop_events` + `shadow_model_pnl` migration (shadow-only, izinli).
2. Paper entry price estimator (depth-walk → ask+buffer fallback), TDD.
3. `_scan_and_execute` `entry_disabled` dalına paper-open hook (live'a dokunmaz, fail-open).
4. Paper monitor: mevcut fiyat altyapısı + 4-model matris + resolve backfill.
5. Air-pocket shadow'u paper stop'larından besle (`is_paper` etiketiyle).

### Açık riskler / unknown

- **unknown:** Paper entry estimate'in gerçek FAK fill'ine ne kadar yakın olduğu — `paper_entry_events` ile denetlenecek, ilk ~20 paper'da kalibre edilir.
- **unknown:** Paper monitor'ün live monitor loop'una ek yük getirip getirmeyeceği — ayrı cadence/throttle gerekebilir (4h shadow pattern'i gibi).
- Paper, air-pocket fill'i **tahmin eder, yaşamaz** → air-pocket guard validasyonu için paper sınırlı; gerçek air-pocket verisi yine live gerektirir (entry açılınca).

---

## Özet Karar

| Soru | Cevap |
|------|-------|
| Canlı değişiklik? | HAYIR — hepsi tasarım/shadow |
| Sıradaki kod adımı | **B: Paper/Shadow Position Tracker** (içinde MFE-breakeven) |
| Neden | Entry kapalı → live stop ölü; paper tek veri kaynağı |
| Paper entry price | depth-walk estimate (mid DEĞİL); fallback ask+taker_buffer |
| Live/paper karışması | Ayrı tablolar + cohort='paper' + confidence='low' |
| Güven | Paper = model sıralaması/yön için; mutlak P&L için değil |
