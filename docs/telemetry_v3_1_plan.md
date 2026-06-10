# Telemetry V3.1 — Data Integrity + Lifecycle Observability — PATCH PLAN

**Amaç:** Toxic high-edge otopsisinde ölçülemeyen 4 boşluğu kapatmak (snapshot_age / spread / hl_drift / lifecycle). Momentum A/B ve latency optimizasyonu PARK. **Salt-gözlem telemetri — model/entry/exit/TP/threshold/clamp DEĞİŞMEZ.**

**Anayasa:** NEW_ENTRIES_ENABLED=False, MIN_EDGE_PCT=0.05, live=0 korunur. Telemetri hata→log+devam (crash yok). Tüm yeni hesaplar in-memory aritmetik (sıfır ek API). TDD: her fix önce test.

---

## Feature flag / kill switch
`config.py`: `TELEMETRY_V31_ENABLED = True` (tek bayrak). Tüm V3.1 hook'ları bu bayrağa bakar; `False` → eski V2 davranışı (yeni alanlar NULL yazılır, hesap yapılmaz). Guardrail sabiti DEĞİL (telemetri bayrağı), ama kapatma tek satır.

## Fix 1 — snapshot_age_ms doldur
- **Dosya:** `main_loop.py` (hook). `compute_legacy_telemetry_v2` zaten `snapshot_age_ms` param + DB kolonu VAR (model_telemetry.py:96, schema'da kolon mevcut) → **sadece main_loop'ta hesapla + geç.**
- **Hesap:** `snapshot_age_ms = now_ms − _sig_ms` (telemetri yazım anı − signal_timestamp_ms). `_sig_ms` zaten main_loop'ta mevcut (satır 480).
- **DB:** Kolon zaten var, ALTER YOK. Eski 73 satır NULL kalır (quarantine doğal).

## Fix 2 — action_spread crossed-fix + flag (edge zehirlenmesin)
- **Dosya:** `data/model_telemetry.py` (compute_v2, satır 176-187).
- **Kök:** `no_ask_observed` (finding) + `no_bid` derived (1−yes_ask) KARIŞIK kaynak → crossed (ask<bid) olabilir.
- **Fix:** spread hesabını tutarlı kaynaktan yap: `spread_consistent = yes_ask − yes_bid` (her iki taraf YES book'tan, action'dan bağımsız mutlak spread). `action_spread` mevcut kalsın AMA `action_spread < 0` ise `spread_crossed_flag=1` + ham `action_bid_raw`/`action_ask_raw` ayrı loglansın. **net_ev/edge hesabı DEĞİŞMEZ** (zaten finding'den gelir, spread'i kullanmaz) → zehirlenme yok.
- **DB:** `model_decision_events` +3 kolon: `spread_crossed_flag INTEGER`, `bid_ask_consistent_spread REAL`, (action_bid_raw/ask_raw zaten action_bid/ask olarak var).

## Fix 3 — hl_drift entry-anı salt-okunur logla
- **Dosya:** `main_loop.py` (hook) + `data/model_telemetry.py` (compute_v2 yeni param `hl_drift_at_entry`).
- **Hesap:** `hl_drift = (cur_price − ref_price) / ref_price` — finding'de `cur_price`/`ref_price` zaten var (satır 495). paper_tracker'daki `hl_drift` mantığıyla simetrik. Sadece LOGLA, karar değiştirmez.
- **DB:** `model_decision_events` +1 kolon: `hl_drift_at_entry REAL`.

## Fix 4 — lifecycle min alanlar (post-exit tick serisi FAZ 2)
- **Dosya:** `execution/paper_tracker.py` (`_update_position_models` + kapanış INSERT).
- **Hesap:** in-memory `_mfe_peak`/`_mae_trough` GÜNCELLENDİĞİ an `elapsed = monotonic − _opened_monotonic` damgala (`_t_mfe`/`_t_mae`). `resolve_ts` = close anı (close_reason='expired'/'resolved' ise resolve, değilse NULL).
- **DB:** `shadow_positions` +5 kolon: `time_to_mfe_s REAL`, `time_to_mae_s REAL`, `resolve_ts TEXT`, `mfe_mae_time_valid INTEGER`, `mfe_mae_time_invalid_reason TEXT`. Tick serisi (paper_tick_series tablosu) = **FAZ 2**, bu plana DAHİL DEĞİL.
- Yeni paper açılışı (aynı process izliyor): `mfe_mae_time_valid=1`, invalid_reason=NULL.

## Fix 4.1 — Restart Recovery (KRİTİK: sahte timestamp önleme)
**Problem:** time_to_mfe_s/mae_s in-memory `_opened_monotonic`'e bağlı. Bot restart/crash → `_active` dict boşalır → önceki process'te açılmış paper'lar için monotonic SIFIRDAN başlarsa SAHTE time üretir, lifecycle/stop analizini zehirler.
- **Dosya:** `execution/paper_tracker.py` (yeni `recover_orphan_open_paper(db_path)`) + `main_loop.py` (startup'ta çağır).
- **Kural:** Bot startup/init anında DB'de `status='open'` kalan paper'lar = ORPHAN (önceki process). Bunlar GERÇEKMİŞ GİBİ yeniden başlatılmaz; açıkça INVALID işaretlenir:
  ```sql
  UPDATE shadow_positions
     SET time_to_mfe_s=NULL, time_to_mae_s=NULL,
         mfe_mae_time_valid=0, mfe_mae_time_invalid_reason='process_restart'
   WHERE status='open'
  ```
- Yeni açılan + aynı process içinde izlenen paper → valid=1, reason=NULL.
- **Kapanış kuralı:** paper'ın in-memory state'i bu process'te varsa → time damgala (valid=1). Yoksa (orphan, state yok) → time YAZILMAZ, valid=0 korunur.
- **Analiz kuralı:** sonraki MFE/MAE-zaman analizlerinde YALNIZCA `mfe_mae_time_valid=1` satırlar kullanılır.

---

## Latency ek yükü sınırlama
- Tüm Fix'ler **in-memory aritmetik** (çıkarma/bölme/damga) — sıfır ek API, sıfır ek DB round-trip (mevcut INSERT'lere kolon eklenir).
- Telemetri yazımı zaten fire-and-forget (schedule_telemetry, non-blocking).
- **Kabul sınırı:** patch sonrası scan_perf p90 ≤ baseline×1.10 (mevcut p90 ~2900ms → sınır ~3200ms). Aşılırsa patch BAŞARISIZ.

## DB kolonları/indexleri özeti (ALTER, hepsi nullable)
- `model_decision_events`: spread_crossed_flag, bid_ask_consistent_spread, hl_drift_at_entry (+ snapshot_age_ms zaten var)
- `shadow_positions`: time_to_mfe_s, time_to_mae_s, resolve_ts
- **Index YOK** (analiz read-only, mevcut tracking_key index yeterli). Eski satırlar NULL = doğal quarantine; N=60 cohort KORUNUR (yeni kolonlar eski satırlarda NULL).

## Eski veri quarantine
ALTER ADD COLUMN → eski 73 satır yeni kolonlarda NULL. Otopsi/calibration sorguları `WHERE <kolon> IS NOT NULL` ile yeni-cohort'u ayırır. V2 vs V3.1 ayrımı: snapshot_age_ms IS NOT NULL (V3.1 işareti). N=60 cohort silinmez/değişmez.

---

## Testler (TDD, unit + integration)
1. `snapshot_age_ms` hook'tan dolu geçiyor (compute_v2 → rec dolu, >0).
2. crossed book (yes_bid>yes_ask) → `spread_crossed_flag=1` + ham bid/ask loglanıyor + `net_ev` DEĞİŞMİYOR.
3. normal book → spread_crossed_flag=0, consistent_spread=yes_ask−yes_bid.
4. `hl_drift_at_entry` doğru hesap ((cur−ref)/ref), YES/NO işaret doğru.
5. `time_to_mfe_s`/`time_to_mae_s` peak/trough anında damgalanıyor (mock monotonic).
6. `resolve_ts` expired/resolved'da dolu, erken-stop'ta NULL.
7. TELEMETRY_V31_ENABLED=False → yeni alanlar NULL, eski davranış.
8. telemetri exception → bot loop crash YOK (mevcut pattern).
9. **decision logic regression:** aynı finding → schedule_paper_open/council kararı V3.1 öncesi/sonrası AYNI (model/entry değişmedi kanıtı).
10. NEW_ENTRIES_ENABLED=False regression.
11. collision_error_count + telemetry_error sayaçları çalışmaya devam ediyor.
12. **Restart Recovery:** açık paper simüle → recover_orphan_open_paper çalışır → time_to_mfe_s/mae_s NULL, mfe_mae_time_valid=0, reason='process_restart'.
13. **No False Timestamp:** restart sonrası orphan open trade için sıfırdan sayaç başlatılıp sahte time_to_mfe/mae DB'ye YAZILAMAZ (in-memory state yok → damga yok).
14. **Clean New Trade:** restart sonrası aynı process'te yeni açılan trade normal izlenir, kapanışta valid=1.
15. **Backward Compatibility:** eski N=60 cohort korunur (yeni kolonlar NULL); analiz `mfe_mae_time_valid=1` filtreler → valid olmayan zamanlar kullanılmaz.

## Canlı/paper karar mantığına dokunulmadığı doğrulama
- Test 9 (decision regression) + grep audit: `fair_value.py`, `council/*`, `MIN_EDGE_PCT`, stop/TP sabitleri DIFF'te YOK.
- hl_drift/snapshot_age yalnızca telemetri compute'a geçer, `_all_model_decisions`/`scout` karar yoluna GİRMEZ.
- Full suite (mevcut 712 test) + yeni 11 test PASS.

## Patch sonrası ilk 5 yeni event manuel doğrulama sorguları
```sql
-- snapshot_age dolu + makul (>0, < birkaç dk)
SELECT event_id, snapshot_age_ms, hl_drift_at_entry, spread_crossed_flag, bid_ask_consistent_spread
FROM model_decision_events WHERE snapshot_age_ms IS NOT NULL ORDER BY id DESC LIMIT 5;
-- crossed flag tutarlı (negatif action_spread → flag=1)
SELECT action, action_bid, action_ask, action_spread, spread_crossed_flag
FROM model_decision_events WHERE snapshot_age_ms IS NOT NULL ORDER BY id DESC LIMIT 5;
-- lifecycle: yeni paper'da time_to_mfe/mae + resolve_ts
SELECT paper_id, time_to_mfe_s, time_to_mae_s, resolve_ts, close_reason
FROM shadow_positions WHERE time_to_mfe_s IS NOT NULL ORDER BY id DESC LIMIT 5;
-- emergency
SELECT 'collision', COUNT(*) FROM ... ; -- log grep COLLISION / telemetry error
```
**Kural:** snapshot_age NULL veya spread_crossed_flag mantıksız → patch açık kabul, rapor üretme.

## Rollback stratejisi (N=60 cohort KAYBETMEDEN)
1. **Önce:** `cp logs/mispricing.db logs/mispricing.db.bak_v31_<ts>` + git tag `pre-v31` @ 89f14c4.
2. **Kod rollback:** `git revert` veya `git checkout 89f14c4 -- <dosyalar>`. ALTER ADD COLUMN geri ALINMAZ ama nullable → eski kod yeni kolonları görmezden gelir (zararsız). N=60 cohort satırları DEĞİŞMEZ.
3. **Latency patlarsa:** TELEMETRY_V31_ENABLED=False (bot restart) → hesaplar durur, kolonlar NULL yazılır. Kod revert gerekmez.
4. **Migration ters giderse:** ALTER try/except (mevcut init_schema pattern) → kısmi ekleme zararsız (nullable). DB backup'tan restore son çare (N=60 backup'ta var).
5. **Bot crash:** önceki commit'e revert + backup DB ile restart. live=0 olduğu için para riski yok.

---

## ACCEPTANCE CRITERIA (hepsi PASS şart)
- [ ] NEW_ENTRIES_ENABLED=False · MIN_EDGE_PCT=0.05 · live open=0 korundu
- [ ] Model/clamp/threshold/entry/exit/TP DEĞİŞMEDİ (test 9 + diff audit)
- [ ] Telemetri hata → bot loop crash ETMEDİ (test 8)
- [ ] collision_error_count + telemetry_error ölçülmeye devam (test 11)
- [ ] scan_perf p90 ≤ baseline×1.10 (~3200ms) — aşılırsa patch BAŞARISIZ
- [ ] snapshot_age_ms / hl_drift_at_entry / spread_crossed_flag ilk 5 event'te dolu+tutarlı
- [ ] lifecycle 3 kolon yeni paper'da dolu (resolve_ts close_reason'a uygun)
- [ ] TELEMETRY_V31_ENABLED=False ile tek-bayrak kapatılabilir
- [ ] Rollback 89f14c4'e N=60 cohort kaybetmeden mümkün (test: bak DB + git tag)
- [ ] **Restart Recovery:** orphan open paper → valid=0/reason='process_restart', sahte timestamp YOK (test 12-13)
- [ ] **Clean new trade** restart sonrası valid=1 (test 14); eski N=60 cohort korunur + analiz valid=1 filtreler (test 15)
- [ ] Full suite 712 + 15 yeni test PASS

## Faz ayrımı
- **Bu plan (V3.1):** Fix 1-4 (snapshot_age + spread-fix + hl_drift + lifecycle-min). Salt telemetri.
- **FAZ 2 (ayrı):** post-exit tick serisi (stopped-but-open tracking, paper_tick_series tablosu) + gerçek stop gözlemi. V3.1 değer kanıtlayınca.
- **PARK:** Momentum/Drift Shadow A/B, latency optimization.
