# Live Execution Faz 2b — Execute Entegrasyonu + Fill-Confirm Plan

**Amaç:** order_intent (2a) iskeletini canlı execute/exit akışına bağlamak: pre-submit intent + tick-validate + order payload + fill-confirm + partial-fill muhasebesi. **Fill kesin doğrulanmadan position AÇIK SAYILMAZ.**

**Anayasa:** live=0, NEW_ENTRIES=False, model/clamp/threshold/TP DEĞİŞMEZ. **Canlı emir YOK** (test=mock). Önce plan+onay, sonra TDD. Heuristic get_trades reconcile = **2c** (bu plan DIŞI).

---

## API doğrulama (read-only, py_clob_client_v2) — TAMAMLANDI
- OrderType: **GTC / FOK / GTD / FAK**. FAK = Fill-And-Kill (IOC eşdeğeri, kalan iptal → **hanging YOK**). Default FOK → kod FAK override (mevcut).
- Tick: `get_tick_size(token)`, `round_down` (V2 market), `ROUNDING_CONFIG`, `is_tick_size_smaller`, `price_valid` — **NATIVE ama submit-içi** (build_order). → **pre-submit ayrı round/validate gerekli.**
- Fill: `post_order` response (size_matched/status) → 2b okuyacak.

## Dosya/satır değişiklik haritası
- `execution/order_intent.py` — `payload_hash` GENİŞLET (canonical, +order_type/tif/tick_rounded_price); `remaining_size` türetme helper (intended−matched).
- `execution/clob_executor.py:execute` — (1) tick-round/validate pre-submit → invalid→REJECTED (network YOK); (2) `has_unresolved_intent` guard → varsa submit YOK; (3) `create_intent` (INTENT_CREATED) pre-submit; (4) submit → `transition(ACCEPTED, server_order_id)`; (5) fill-confirm: response size_matched → FILLED/PARTIAL_FILLED; (6) **position yalnız FILLED/PARTIAL** (ACCEPTED≠açık).
- `execution/position_store.py:sell_position` — aynı intent+fill-confirm akışı (exit).
- `db/schema.py` — requested_size = intended_size (mevcut); remaining_size türetilir (kolon YOK).

## 1. Payload Hash Contract (RİSK)
- **Alanlar:** `token_id, side, intended_price (tick-rounded), intended_size, order_type, time_in_force, slippage_buffer`. **2a'daki minimal hash (token|side|price|size) GENİŞLER → eski intent hash'leri farklı (geçmiş etkilenmez, yeni format).**
- **Canonical:** `json.dumps(sort_keys=True, separators)` → stable ordering. sha256.
- **Test:** token/side/price/size/order_type değişince hash DEĞİŞİR; dict key sırası değişince hash DEĞİŞMEZ (canonical).

## 2. Order Payload / TiF (RİSK)
- **FAK (IOC)** — mevcut derinlik dolar, kalan iptal → **hanging/askıda emir YOK.** GTC/GTD YASAK (hanging). FOK default → FAK explicit override.
- intent kaydına `order_type=FAK` + `time_in_force` bağlanır (payload_hash + audit).
- **Test:** create_market_order payload order_type=FAK (mock contract); GTC/GTD üretilmez.

## 3. Tick-size / Rounding (RİSK)
- **PRE-SUBMIT:** quote.ask/bid → `get_tick_size(token)` + `round_down` (entry ask yukarı-yuvarlama riskli → market round_down) + `price_valid`. **Invalid tick → network call YAPILMADAN REJECTED/FATAL** (intent REJECTED, submit yok).
- Native price_valid submit-içi → ona güvenme; pre-submit ayrı validate (Fiyat Anayasası: varsayma).
- **Test:** invalid tick price → REJECTED + create_market_order ÇAĞRILMAZ (mock assert_not_called).

## 4. Partial Fill Muhasebesi (RİSK)
- FAK partial → `size_matched < intended_size` → **PARTIAL_FILLED**; position **yalnız executed_size** (size_matched) kadar açılır. **Kalan/cancelled hayali pozisyon DEĞİL.**
- `remaining_size = intended_size − size_matched` (türetilir). position_store shares = size_matched.
- size_matched=0 → position AÇILMAZ (fill yok).
- **Test:** size_matched=6 / intended=10 → PARTIAL_FILLED, position shares=6, remaining=4 hayali değil; size_matched=0 → position yok.

## 5. Fill-Confirm Invariant (RİSK)
- **ACCEPTED ≠ açık pozisyon.** Yalnız `is_position_open` (FILLED/PARTIAL_FILLED) → position_store'a açık pozisyon yazılır.
- Submit response belirsiz/ACCEPTED-fill-yok → position AÇILMAZ (status polling 2c; 2b'de ACCEPTED→position yok, FILLED bekle).
- **Test:** ACCEPTED state → position_store'a YAZILMAZ; FILLED/PARTIAL → yazılır.

## Diğer zorunlu başlıklar
- **API Contract Gate:** create_market_order(FAK, tick-rounded price, side, amount) payload + post_order response (size_matched/status) mock contract.
- **Price Lineage post-2b:** entry=ask (tick-rounded), exit=bid; /price kritik yolda 0 (regression). Kod-PASS + runtime PENDING.
- **Decision/exec regression:** scout DEĞİŞMEZ; entry=ask/exit=bid (Faz1) korunur; 2a guard (unresolved blok) entegre.
- **Latency:** intent DB yazımı + tick-resolve execution path (live), scan loop DEĞİL → scan latency etkilenmez.
- **Rollback:** git tag pre-2b + DB backup. order_intent kolon yok (2a tablo mevcut). live=0 → para riski yok. Kademeli commit.

## Acceptance (live açmadan önce, 2b kapsamı)
- [ ] payload_hash canonical + genişletilmiş alanlar (test)
- [ ] tick-invalid → REJECTED, network call YOK (test)
- [ ] partial fill → position=size_matched, kalan hayali değil (test)
- [ ] ACCEPTED ≠ açık; FILLED/PARTIAL → position (test)
- [ ] unresolved intent varken submit YOK (2a guard entegre)
- [ ] FAK/hanging-yok payload (test) · full suite + contract gate PASS
- [ ] NEW_ENTRIES=False, live=0, canlı emir yok korundu

## Kapsam Sınırı
2b = execute entegrasyonu + fill-confirm + partial + tick + payload-hash. **Heuristic get_trades reconcile + SUBMITTED_UNKNOWN recovery loop + kill-switch tetik = 2c.** Error sınıflandırma + execution_errors telemetri = 2d.
