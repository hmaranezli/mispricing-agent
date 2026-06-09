# Shadow A/B Framework + Fair-Value Model Audit — Tasarım Dokümanı

> **Durum:** TASARIM/ŞARTNAME. Kod/migration/restart YOK. Onaya sunulur.
> **Guardrail:** NEW_ENTRIES_ENABLED=False · MIN_EDGE_PCT=0.05 · live open=0 (doğrulandı).
> **Tarih:** 2026-06-09 · Bağlam: [[fair_value_calibration_failure]] — legacy model overconfident (fair %67 vs win %14, Brier 0.39).

## 0. Benim 3 kritik eklemem (itiraz değil — tasarımı güçlendiren nüans)

1. **POST-MORTEM ÖNCE, candidate SONRA.** Telemetri (GÖREV 2) ile `model_vol` + `realized_vol_proxy` topla → vol_error'u KESİNLEŞTİR → ANCAK O ZAMAN candidate tasarla. Aksi halde "adaptive vol" kör atış. Sıra: telemetri → veri → post-mortem kesinleşir → candidate.

2. **LEGACY ZATEN REALIZED VOL KULLANIYOR** (kod teyidi: `scout._get_all_vols` → `calculate_realized_volatility` 1m×60dk; ASSET_VOL sadece fallback). Yani Candidate-1 "realized vol kullan" DEĞİL — legacy bunu yapıyor zaten. Gerçek fark **window/clamp/annualization düzeltmesi** olmalı (aşağıda post-mortem).

3. **OVERFIT/LOOK-AHEAD YASAĞI.** Candidate parametreleri (EWMA span, drift katsayısı, clamp) geçmiş 42 paper'a FIT EDİLMEYECEK — teori/literatürden ÖNCEDEN sabitlenip İLERİYE-DÖNÜK shadow'da test edilecek. Geçmişe fit = overfit = sahte başarı (survivor-bias dersinin tekrarı).

---

## GÖREV 1 — Shadow A/B Framework (deterministik snapshot)

**Eşleme ilkesi:** Tek snapshot, çok model. Latency/farklı-book/farklı-timestamp kirliliği YOK.

```
_ab_snapshot_loop (paper scan loop'a entegre veya ayrı):
  1. snapshot al: snapshot_id (uuid), timestamp, market/slug, book (get_book BİR KEZ),
     p_now (HL), p_ref, best_bid/ask, spread, depth, realized_vol_proxy (entry-time)
  2. her model_version için PURE function çağır (snapshot'ı tüket, kendi I/O YOK):
       fair = MODEL(p_now, p_ref, secs, vol_inputs, snapshot)
  3. her model çıktısı AYNI event_id + AYNI snapshot_id altında, FARKLI model_version ile loglanır
```

- `fair_yes` zaten saf fonksiyon (p_now, p_ref, secs, vol) → snapshot'tan beslenir, ek get_book YOK.
- Candidate modeller de saf: aynı snapshot input, farklı vol/drift mantığı.
- **Kritik:** NEW model ASLA ayrı book çekmez (legacy'den sonra fiyat kayar → A/B kirlenir).

## GÖREV 2 — Telemetry Şartnamesi

**Yeni tablo: `model_decision_events`** (snapshot anında, OUTCOME YOK):

| alan | açıklama |
|------|----------|
| event_id, snapshot_id, timestamp | eşleme anahtarları |
| market_id/slug, asset, timeframe, action | market |
| **model_version** | LEGACY / ADAPTIVE_VOL / MOMENTUM_DRIFT |
| ref_price, p_now, best_bid, best_ask, spread | fiyat snapshot |
| depth_summary, snapshot_age_ms | likidite |
| **model_vol, realized_vol_proxy_at_entry, vol_source, vol_window** | ← EKSİK OLAN, EN KRİTİK |
| sigma_t, z_score, drift_term, momentum_term | model iç değişkenleri |
| fair_yes, fair_no, action_fair | model çıktısı |
| fee_adjustment, net_ev, fair_gap, edge_bin | edge |
| decision_threshold, would_enter (bool) | karar (shadow, canlı DEĞİL) |

**Ayrı tablo: `model_outcome_link`** (resolved olunca event_id/snapshot_id ile bağlanır):
- resolved_outcome, close/expiry_pnl, tp30_valid, policy_net_contribution
- brier_contribution, logloss_contribution

**KRİTİK AYRIM:** Brier/calibration_gap/policy_net snapshot anında HESAPLANMAZ. Snapshot = sadece input/output log. Metrikler resolved geldikten SONRA event_id/snapshot_id üzerinden hesaplanır. (Anti-leakage: outcome'u entry telemetrisine karıştırma.)

## GÖREV 3 — Model Candidate'leri (sadelik ilkesi)

| Model | Tanım | Hipotez |
|-------|-------|---------|
| **LEGACY** (baseline) | driftless GBM, realized vol (1m×60dk, clamp [0.30,3.00]) | benchmark |
| **ADAPTIVE_VOL** | aynı denklem, **DÜZELTİLMİŞ vol**: kısa-pencere (5-15dk'ya uygun) EWMA, clamp gevşetilmiş/kaldırılmış | overconfidence vol-underestimate'ten ([[fair_value_calibration_failure]]) |
| **MOMENTUM_DRIFT** | adaptive vol + basit drift term (örn son N-dk getiri × ölçeklenmiş) | driftless varsayım mean-reversion/momentum'u kaçırıyor |

**Kural:** Bayesian/ML/black-box YOK. Bu 3 model calibration+Brier+policy_net'te hâlâ kötüyse SONRA tartışılır. Basitlik öncelik; karmaşıklık hatayı saklar. **Drift/momentum term basit + ölçülebilir** (katsayı önceden sabit, overfit yok).

## GÖREV 4 — Comparison Protocol (resolved universe)

Her model için resolved universe'de:
- calibration_gap, Brier, log loss
- TP30_valid_rate, policy_net_conservative_outcome (payda=total resolved, tp_hit DEĞİL)
- toxic_high_edge_rate (net_ev 0.09+ win rate)
- edge-bin performance, asset/action breakdown
- **ALL_ASSETS / EX_XRP / XRP_ONLY** ayrı
- right-censored (açık) pozisyonlar AYRI (karara katılmaz)

**Başarı koşulu (HEPSİ gerekli):** NEW model tek slice'ta değil, **tüm resolved universe'de** legacy'den: daha iyi calibration + daha iyi Brier + daha iyi policy_net + daha düşük toxic_high_edge. Tek pozitif asset / küçük-N slice YETERSİZ.

## GÖREV 5 — Legacy Post-Mortem (neden fair 0.67 → win 0.14?)

Kod-temelli şüpheli sıralaması (en olası → en az):

1. **VOL CLAMP [0.30, 3.00] (en güçlü şüpheli):** `calculate_realized_volatility` annualized vol'ü 3.00'a (=%300 yıllık) clamp'liyor. Crypto 5-15dk pencerede gerçek vol bunu aşabilir → **sistematik underestimate** → sigma_t küçük → z büyük → fair ekstreme (overconfident). XRP/SOL high-vol dönemde clamp'e çarpıyor.
2. **60dk window vs 5-15dk resolution:** 60 dakikalık ortalama vol, son 5-15dk'nın spike'ını yansıtmıyor (lag). Rejim değişiminde fair gecikiyor.
3. **drift=0 varsayımı:** Kısa vadede momentum/mean-reversion var; driftless model yön bilgisini kaçırıyor. Ama scout `_drift_ok` entry filtresi var → kısmen telafi (yine de fair hesabı drift'siz).
4. **annualization round-trip:** 1m vol → ×√525600 (yıllık) → fair'de ÷√31557600 (saniye→yıl). Term-structure düz varsayımı; kısa vadede vol daha yüksekse hata.
5. ref_price timing (pencere açılışı HL — doğru görünüyor), NO dönüşümü (1−yes, simetrik), fee (standart) — düşük şüphe.
6. flash-spike/microstructure — ikincil (TP-tradability tarafı).

**Telemetri (GÖREV 2) bunu kesinleştirir:** model_vol vs realized_vol_proxy + sigma_t logu → clamp/window hipotezi doğrulanır/çürütülür.

## GÖREV 6 — Guardrail ✅
NEW_ENTRIES_ENABLED=False · MIN_EDGE_PCT=0.05 · live open=0 (doğrulandı).

## Migration Planı (öneri, henüz yazılmadı)
- `model_decision_events` (yeni tablo, ~30 kolon)
- `model_outcome_link` (yeni tablo, resolved bağlama)
- Mevcut shadow tablolar dokunulmaz (legacy benchmark korunur).
- Hepsi shadow; live execute'a bağlanmaz.

## Önerilen Uygulama Sırası (onay sonrası, her biri TDD)
1. **Telemetri katmanı** (model_decision_events + outcome_link + A/B snapshot pipeline) — LEGACY tek model, model_vol/realized_vol logla.
2. Veri topla (40-50 resolved) → **post-mortem kesinleştir** (clamp/window hipotezi).
3. Post-mortem'e göre ADAPTIVE_VOL candidate (önceden-sabit parametre).
4. Shadow A/B (legacy vs adaptive) → comparison protocol.
5. Gerekirse MOMENTUM_DRIFT.
6. Hiçbir model tüm-evren 4-metrikte legacy'yi geçmezse → karmaşık model / strateji-iptali insan kararı.

---

## Özet Karar
| Soru | Cevap |
|------|-------|
| Bu aşama | Tasarım/şartname — kod/migration/restart YOK |
| Önce ne | Telemetri (model_vol logla) → post-mortem kesinleştir → SONRA candidate |
| Legacy zaten | realized vol kullanıyor → candidate "doğru window/clamp" olmalı |
| Overfit koruması | candidate parametreleri önceden-sabit, ileriye-dönük shadow |
| Başarı | tüm-evren 4-metrik (calibration+Brier+policy_net+toxic) legacy'yi geçmeli |
| Canlı karar | YOK — yeni model shadow A/B'de kanıt üretene kadar |
