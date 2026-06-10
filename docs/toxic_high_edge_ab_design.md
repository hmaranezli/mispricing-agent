# Toxic High-Edge — Multi-Hypothesis Ayrıştırma + Shadow A/B Design

**Amaç:** net_ev 0.09+ bininde hold_win=0.471 (coin-flip altı, gap −0.238) çöküşünün NEDENİNİ ayrıştırmak. **Momentum'a ATLAMA** — büyük "edge" çoğu zaman gerçek değil, ölçüm artefaktıdır (bayat book / geniş spread / düşük likidite / TTE).

**Anayasa:** Model/entry/exit/TP/threshold DEĞİŞMEZ. Live yok. Önce OFFLINE, sonra gerekirse shadow gözlem.

## Aday hipotezler ve mevcut proxy değişkeni

| Hipotez | Proxy (V2'de LOGLU) | Beklenen imza (0.09+ çöküşse) |
|---------|---------------------|-------------------------------|
| momentum/drift eksikliği | entry-anı HL yönü vs PM action (hl_drift) | yüksek-edge'de HL momentum PM yönüne TERS |
| stale book / data freshness | `snapshot_age_ms` | yüksek-edge event'lerde snapshot daha BAYAT |
| spread / liquidity bozulması | `action_spread`, `best_bid/ask` | yüksek-edge'de spread GENİŞ (mid yanıltıcı, fill kötü) |
| time-to-expiry etkisi | `time_to_expiry_seconds` | yüksek-edge resolve'a ÇOK yakın (gürültü) |
| latency / API etkisi | `scan_perf` + snapshot_age | yüksek-edge yavaş-scan'lerde yoğun |

## Yöntem (iki adım)

**Adım 1 — OFFLINE korelasyon (YENİ KOD/MODEL YOK, mevcut N=60+ veri):**
0.09+ edge event'lerini ayır; her proxy (snapshot_age / action_spread / TTE / hl_drift) ile `hold_win` korelasyonu + 0.03-0.06 bini ile KARŞILAŞTIR. Hangi değişken yüksek-edge'de anormal? Bu, root cause'u 5 hipotezden 1-2'ye indirir. **N=60 ile KISMEN şimdi başlanabilir** (0.09+ n=17, low-N → daha çok high-edge event birikmeli).

**Adım 2 — Shadow gözlem (sadece kazanan hipotez için, paper, live yok):**
En güçlü sinyale `toxic_flag` telemetri kolonu (ör. momentum_conflict / stale / wide_spread) — entry'yi DEĞİŞTİRMEZ, sadece etiketler. Flag'li vs flag'siz high-edge cohort win karşılaştır. Doğrulanırsa → entry filtresi adayı (ayrı tur).

## En küçük güvenli patch
**Sıfır kod:** Adım 1 tamamen offline analiz (mevcut V2 telemetri). Önce bunu çalıştır — belki tek bir proxy (ör. snapshot_age veya spread) çöküşü açıklar, momentum modeline hiç gerek kalmaz.
**Eğer patch gerekirse (en küçük):** high-edge + bozuk-proxy (ör. snapshot_age > X veya spread > Y) event'lerine `toxic_flag` yazan SALT-GÖZLEM telemetri kolonu. Entry/threshold/model'e DOKUNMAZ. Filtre/veto ancak shadow doğrularsa, ayrı tur.

**Kritik:** Yüksek-edge çöküşü stale-book/spread artefaktıysa çözüm momentum DEĞİL, data-freshness/likidite veto'sudur. Adım 1 bunu ayırmadan model yazılmaz.
