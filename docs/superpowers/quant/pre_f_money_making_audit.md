# Pre-F Money-Making Audit

> **Meta:** `Pre-F Audit: Ops-Chain (D#1-D#11) Verified, Live-Gate (D#2/D#7) Closed`
> Buradaki **"Closed" = canlı kapı KİLİTLİ/ENGELLİ** (live access shut) — D#2/D#7 *tamamlandı*
> anlamına GELMEZ; o gateler hâlâ açık insan kapılarıdır. Bu artifact bir **Pre-F money-making audit**
> kapısıdır: Master Plan F (gerçek para/ölçek) ÖNCESİNDE para-kazanma mantığının OFFLINE denetimi.
> Paper Soak DEĞİL, canary/live onayı DEĞİL. Tarih: 2026-06-14. Anayasa (CLAUDE.md) üsttedir.

## 1. Scope and meta marker

- Kapsam: para-kazanma mantığının **offline data only** denetimi; üç ekseni AYIR (§4).
- `D#1-D#11 readiness verified` (operasyonel güvenlik PASS) — ama bu **para kazanma kanıtı DEĞİL**.
- `no live API`, `no Telegram`, `no live DB` — hiçbir canlı etkileşim yok; `D#7 phase-2 balance/auth
  probe not run`.

## 2. Inputs reviewed

- `docs/superpowers/evidence/production_readiness_packet.md` (D#9), `independent_verifier_d10.md`
  (D#10), `gemini_adversarial_review_d11.md` (D#11).
- Recorded memory evidence (aşağıda §5 — YENİ hesaplanmadı, geçmiş kayıt).
- Offline edge/kalibrasyon veri yüzeyi (kod): `data/model_telemetry.py`, `execution/paper_tracker.py`,
  `execution/air_pocket_shadow.py`, `data/shadow_quote.py` + ilgili testler (telemetry v1/v2/v3.1,
  paper_tracker, edge_bucket_shadow, fee_rate). **Bu turda re-run/yeniden hesap YAPILMADI** (RED→GREEN
  artifact kapısı; metrik materyalizasyonu sonraki adım).

## 3. PASS/FAIL recommendation

- **PASS/FAIL recommendation = FAIL/BLOCKED on edge correctness.**
- **PASS VERİLMEDİ.** Operasyonel zincir (D#1–D#11) yeşil olsa da `edge correctness` mevcut kanıtla
  kanıtlanamaz; üstelik `Poly API data fidelity` doğrulanmadığı için "model bozuk" sonucu bile
  henüz temiz değil (§4/§8). `production canary NOT approved` korunur.

## 4. Code/logic correctness vs statistical edge correctness vs data fidelity correctness

Üç AYRI eksen — birini geçmek diğerini geçmez:

1. **Code/logic correctness** — `entry/exit correctness`, `fee/slippage logic verified`, order
   construction, `reject reasons` routing. Offline test edilebilir; büyük ölçüde testlerle kapsanmış
   (likely PASS-able). **Ama bu para kazandırmaz** — yalnız "boru hattı doğru bağlı" demek.
2. **Statistical edge correctness** — `fair price` kalibrasyonu, `expected edge`, `calibration
   metrics` (Brier/reliability), `win-rate vs loss-magnitude`, `paper PnL`. **Mevcut kanıtla
   BLOCKED/FAIL** (§5).
3. **Data fidelity correctness** — `Poly API data fidelity` + Hyperliquid besleme doğruluğu.
   **NOT VERIFIED** — `API usage audit` tamamlanana kadar (§8). `garbage-in garbage-out`: yanlış
   `market/query semantics`, `adjusted/unadjusted data`, `timestamp/latency assumptions` SAHTE edge
   üretebilir.

> **Claude eleştirisi (kullanıcının 3. eksen önerisine):** Bu eksen kritik ve doğru. §5'teki
> "model miscalibration" (Brier 0.39) sonucu, **data fidelity hatalarıyla CONFOUNDED olabilir** —
> ör. Hyperliquid fiyatı yanlış zaman penceresinde/latency ile Polymarket'e kıyaslanıyorsa, ya da
> stale/adjusted veri kullanılıyorsa, model "overconfident" görünür ama kök neden VERİ. Yani modeli
> tek suçlu varsaymak hatalı olur: data fidelity audit'i, kalibrasyon audit'inden ÖNCE (veya
> paralel) gelmelidir; aksi halde sağlam modeli yanlış veriyle yeniden eğitip aynı duvara çarparız.

## 5. Recorded adverse edge evidence

**Aşağıdakiler RECORDED PRIOR EVIDENCE / memory evidence'tır — bu turda YENİDEN HESAPLANMADI:**

- `fair price` overconfidence: **fair %67 vs actual win %14**; **Brier 0.39 > random** (model audit
  zorunlu; exit ayarı çözmez). [recorded: fair_value_calibration_failure]
- Exit imhası: giriş alfası VAR (peak +%37) ama **hold-to-resolve win 2/18**; `take-profit +20/+30`
  pozitif sinyal. [recorded: alpha_exit_side]
- **XRP kötü** (asset-bağımlı felaket); **5m eksik** (taranmıyor). [recorded]
- Epoch 3 kanama → **NEW_ENTRIES_ENABLED=False** (canlı entry kapalı). [recorded: acil_risk_modu]

`win-rate vs loss-magnitude`: hold-to-resolve düşük win + büyük kayıp asimetrisi; take-profit kısa
asimetriyi düzeltiyor görünüyor — ama bu da yeniden ölçülmeli (§7).

## 6. Fee/slippage/reject/paper-PnL sanity inventory

- `fee/slippage logic verified`: fee/slippage edge'e ekleniyor (test_fee_rate + system_audit kaydı) —
  kod tarafı offline doğrulanabilir; net-edge formülü mevcut.
- `reject reasons`: scout→council→gate veto'ları + execution recovery reason'ları loglanıyor.
- `paper PnL`: `paper_tracker` + edge_bucket_shadow mevcut; get_book sorting bug fix sonrası temiz
  paper 3/3 pozitif EV gözlemi VAR ama N=3 — istatistiksel anlam YOK. [recorded: paper_shadow_tracker]
- **Envanter mevcut; ama bunlar "code present" kanıtı — "edge proven" DEĞİL.**

## 7. Missing calibration metrics

Henüz materyalize edilmemiş (F öncesi ZORUNLU), offline hesaplanmalı:
- Brier skoru + reliability curve (resolved paper/shadow ledger'dan), edge-bucket × asset kırılımı.
- fair-vs-realized win-rate eğrisi (overconfidence ölçümü).
- `win-rate vs loss-magnitude` dağılımı + exit politikası karşılaştırması (hold vs TP+20/+30).
- net `expected edge` (fee+slippage sonrası) bucket/asset bazında, anlamlı N ile.
- per-asset (XRP dahil) + per-timeframe (5m dahil) ayrışım.

## 8. Required offline remediation sequence

1. **Poly API data fidelity & `API usage audit` (ÖNCE):** kesin API provider/docs versiyonu;
   `market/query semantics`; `timestamp/latency assumptions`; aggregation/`adjusted/unadjusted data`
   kuralları; condition/status kodları; missing/stale data handling; fee/slippage uyumu;
   `data ingestion correctness`. **Modeli tek başarısızlık kaynağı VARSAYMA** — `garbage-in
   garbage-out` sahte edge'in kök nedeni olabilir.
2. Offline **calibration metrics** artifact (§7 metrikleri materyalize).
3. Entry-alpha vs exit-destruction → exit/TP politikası kararı.
4. Per-asset gating (XRP) + 5m timeframe.
5. Net-edge yeniden hesap. Ancak Brier < random + temiz paper'da anlamlı-N pozitif net EV →
   Paper Soak → F.

## 9. Live gates remain closed

- `production canary NOT approved`. Canlı kapı KİLİTLİ: D#2 (insan-only live gate) + D#7 phase-2
  (canlı balance/auth — Gemini'ye göre Critical blocker) AÇIK. Canlıya geçiş yalnız insanın açık
  yazılı komutuyla (anayasa madde 2). `D#7 phase-2 balance/auth probe not run`.

## 10. Next required artifact

- **Poly API data fidelity & usage audit** (offline, docs/usage temelli) — bu, calibration
  metriklerinden ÖNCE gelmeli (data confounder'ı ele). Ardından offline calibration metrics artifact.
- Bu audit `FAIL/BLOCKED on edge correctness` olarak kilitlenir; F'e geçiş bu zincir tamamlanıp
  pozitif kanıt üretilmeden değerlendirilemez.
