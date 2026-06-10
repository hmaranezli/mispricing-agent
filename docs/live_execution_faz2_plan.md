# Live Execution Faz 2 — Order Payload & Execution Engine Plan

**Amaç:** Canlı emir gönderim+teyit mekanizmasını order payload / limit price / fill-confirm / idempotency / timeout-recovery / kill-switch / reconciliation açısından kurumsal execution standardına taşımak. **Gerçek para çekirdeği.**

**Anayasa:** live=0, NEW_ENTRIES_ENABLED=False, model/clamp/threshold/TP DEĞİŞMEZ. **Canlı emir gönderilmeyecek** (test = mock/contract). Önce plan+onay, sonra TDD.

---

## 0. IDEMPOTENCY CAPABILITY AUDIT (read-only, py_clob_client_v2) — TAMAMLANDI
| Soru | Bulgu |
|------|-------|
| client_order_id / idempotency-key (pre-submit)? | **YOK** (grep idempoten=0; OrderArgs'ta yok) |
| salt deterministik mi? | **HAYIR — `generate_order_salt()` RANDOM** (order_utils/utils.py:5). Her submit farklı EIP-712 hash → **server-side dedup YOK** |
| nonce? | EIP-712 imza nonce (cancel-all replay) — order-level idempotency DEĞİL |
| order_id? | **Server response** (post-submit, `clob_types:253 orderID`). PRE-submit yok |
| status sorgu? | ✅ `get_order(order_id)` + `get_trades(...)` (post-submit reconcile) |
| timeout sonrası aynı args retry güvenli mi? | ❌ **HAYIR — DUPLICATE riski** (salt random, dedup yok) |
| tick_size / price_valid? | ✅ Native (`create_market_order` tick_size resolve + `price_valid`) |

**SONUÇ:** Native pre-submit idempotency YOK → **LOCAL idempotency ZORUNLU** (order_intent_id + DB unique + pre-submit INTENT kaydı + post-submit orderID eşleme + reconcile). Status polling get_order/get_trades ile MÜMKÜN.

---

## 1. Dosya/satır değişiklik haritası
- `execution/clob_executor.py:execute` — order_intent kaydı (pre-submit) → create_market_order → response/fill-confirm → state machine; timeout/exception sınıflandırma.
- `execution/position_store.py:sell_position` — exit emri aynı intent/fill-confirm akışı.
- `db/schema.py` — `order_intents` tablosu (state machine) + `execution_errors` tablosu.
- `main_loop.py` — reconciliation loop (ayrı cadence) + unknown-state → kill-switch tetik.
- `config.py` — MAX_SLIPPAGE_CAP, ORDER_TIMEOUT_S, RECONCILE_INTERVAL_S (veri-kalite/risk sabitleri).

## 2. BUY/SELL → explicit bid/ask (Faz 1'de BİTTİ — REGRESSION)
Faz 1'de yapıldı (get_quote.ask/bid). **Faz 2 yeni iş DEĞİL** → sadece regression: order limit price quote.ask (entry) / quote.bid (exit) korunuyor mu (test).

## 3. Entry=ask, exit/mark=bid invariant (Faz 1 korundu + payload'a taşındı)
- Entry limit = `quote.ask + PRICE_PREMIUM` (≤ MAX_SLIPPAGE_CAP). Exit limit = `quote.bid − PRICE_PREMIUM`. Regression test.

## 4. API Contract Gate testleri
- create_market_order payload: side, amount, price, FAK, tick_size — beklenen alanlar (mock client contract test).
- get_order/get_trades response şeması (orderID, status, size_matched) — contract.
- salt random / dedup-yok belgelendi → local idempotency gerekçesi.

## 5. Price Lineage post-patch tekrar
Order limit price = QuoteProvider (ask entry/bid exit), tick-rounded. /price kritik yolda 0 (regression). Kod-seviyesi PASS + runtime PENDING (live=0).

## 6. Decision/live execution regression
- Decision (scout) DEĞİŞMEZ. Live entry/exit fiyat-yönü Faz 1 korunur.
- Order akışı: INTENT→submit→fill-confirm mock testleri. Full suite PASS.

## 7. Latency etkisi
order_intent DB yazımı (pre-submit) + fill-confirm polling = execution path (live), scan loop DEĞİL → scan latency etkilenmez. Reconcile ayrı cadence (main loop bloklamaz). p90 raporlanır.

## 8. Rollback planı
DB backup + git tag `pre-live-exec-faz2`. order_intents/execution_errors nullable ALTER (geri-zararsız). Kod revert. live=0 → para riski yok. Kademeli: schema → idempotency → fill-confirm → reconcile → kill-switch (her biri ayrı commit+test).

## 9. Live açmadan önce acceptance criteria
- [ ] Local idempotency: order_intent_id + DB UNIQUE → duplicate submit imkansız (test)
- [ ] Fill kesin doğrulanmadan position AÇIK SAYILMAZ (state machine)
- [ ] Timeout → SUBMITTED_UNKNOWN → reconcile (get_trades) → otomatik 2. emir YOK
- [ ] Unknown state → NEW_ENTRIES kill-switch tetik
- [ ] MAX_SLIPPAGE_CAP aşılırsa order GÖNDERİLMEZ
- [ ] retryable/fatal hata sınıflandırma (signature/nonce/balance/allowance/funds = fatal)
- [ ] execution_errors telemetri (reason + retry_class)
- [ ] full suite + contract gate PASS · latency p90 ≤ sınır
- [ ] NEW_ENTRIES=False, live=0 korundu (Faz 2 canlı AÇMAZ)

## 10. Limit Price / Order Payload Invariant
- **Mevcut:** `create_market_order(MarketOrderArgs(side=BUY, amount=$, price=worst_price, order_type=FAK))`, worst_price = `quote.ask + PRICE_PREMIUM` (Faz1).
- **Limit kaynağı:** entry → quote.ask+buffer; exit → quote.bid−buffer (book-derived, side kelimesi değil).
- **Taker/maker:** FAK = taker; maker (askıda) YASAK.
- **Tick/rounding:** native `tick_size` + `price_valid`; limit price tick'e yuvarlanacak (round → price_valid kontrol; invalid → order YOK).
- **TIF:** **FAK (IOC)** — askıda/hanging emir YOK (kalan otomatik iptal). FOK default → FAK override (Faz1 mevcut, test).
- **Partial fill:** FAK kısmi → response `size_matched`/fill → **position shares = GERÇEK fill** (amount değil); fill=0 → position AÇILMAZ.
- **Slippage buffer + MAX_SLIPPAGE_CAP:** entry ask+PREMIUM ama `≤ ask×(1+MAX_SLIPPAGE_CAP)`; aşılırsa order YOK (runaway koruması).
- **Hanging cleanup:** FAK → askıda kalmaz; yine de fill-confirm sonrası açık-emir kontrolü (get_order status).
- **Payload contract testleri:** mock client → MarketOrderArgs alanları + FAK + tick-rounded price.

## 11. Idempotency / Timeout / Unknown State — STATE MACHINE
**order_intent_id:** client-üretilen UUID (pre-submit). **DB:** `order_intents(order_intent_id PK/UNIQUE, slug, token_id, side, limit_price, amount, payload_hash, status, server_order_id, size_matched, created_at, updated_at)`. payload_hash = sha256(token+side+price+amount).
**State machine:**
```
INTENT_CREATED → (submit) → SUBMITTED_UNKNOWN
  ├─ response OK → ACCEPTED → (poll) → PARTIAL_FILLED / FILLED
  ├─ response REJECTED → REJECTED
  └─ timeout/no-response → SUBMITTED_UNKNOWN → RECOVERY_REQUIRED → (reconcile) → FILLED/CANCELLED/REJECTED
```
- **Submit ÖNCESİ** INTENT_CREATED kaydı (DB UNIQUE) → aynı intent iki kez submit edilemez.
- **Timeout:** SUBMITTED_UNKNOWN; **otomatik 2. emir YASAK**; reconcile (get_trades/get_order) ile akıbet netleşene kadar bekle.
- **Unknown akıbet netleşmeden yeni emir ENGELLENİR** (o token/slug için).
- **Unknown state → NEW_ENTRIES kill-switch / emergency pause tetik** (RECOVERY_REQUIRED varsa yeni entry durur).
- **Fill-confirm:** FILLED/PARTIAL_FILLED (size_matched>0) olmadan position AÇIK SAYILMAZ.

## 12. Execution Error / Reconciliation
- **4xx/5xx:** retryable (timeout, 5xx geçici, rate-limit) vs **fatal** (signature/nonce/balance/allowance/insufficient_funds, 4xx invalid) → fatal retry YOK.
- **Order accepted, fill yok:** `get_order(order_id)` status polling (N deneme, ORDER_TIMEOUT_S) → fill kesinleşene kadar position açık değil.
- **Reconciliation loop:** main_loop ayrı cadence (RECONCILE_INTERVAL_S) → SUBMITTED_UNKNOWN/RECOVERY_REQUIRED intent'leri get_trades ile eşle, state güncelle. Main loop'u BLOKLAMAZ (ayrı task).
- **Rejection telemetry:** `execution_errors(order_intent_id, http_status, reason, retry_class, ts)`.
- **Kill-switch iptal:** kill-switch tetiklenince aktif/bekleyen intent iptali (cancel) ayrı task, main loop bloklamaz.
- **Exception contract/integration testleri:** timeout/4xx/5xx/no-response mock → doğru state + no-duplicate + kill-switch tetik + execution_errors yazımı.

---

## Faz 2 alt-faz (en küçük güvenli artımlar)
- **2a — Idempotency iskeleti:** order_intents tablosu + order_intent_id + DB UNIQUE + INTENT_CREATED pre-submit. (duplicate-imkansız temel)
- **2b — Fill-confirm + state machine:** submit→ACCEPTED→FILLED/PARTIAL; fill olmadan position açık değil.
- **2c — Timeout/unknown + reconcile + kill-switch:** SUBMITTED_UNKNOWN → reconcile loop → unknown→kill-switch.
- **2d — Error sınıflandırma + execution_errors telemetri + slippage cap.**
Her alt-faz TDD + ayrı commit + guardrail. Hepsi PASS → canlı açma kararı (AYRI insan onayı, bu plan DIŞI).

## Live açmadan önce BLOCKER listesi
1. 2a-2d hepsi PASS (idempotency, fill-confirm, timeout/unknown, error/reconcile).
2. Runtime sample (live=0 → henüz yok; canlı-öncesi paper/shadow execution simülasyonu).
3. Insan onayı (DRY_RUN=False, NEW_ENTRIES=True) — bu plan KAPSAMI DIŞI.
