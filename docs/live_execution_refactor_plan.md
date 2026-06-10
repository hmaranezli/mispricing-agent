# Live Execution Path Refactor — Minimal Patch Plan

**Amaç:** Canlı execution path'teki 5 `/price`-ters kullanımını QuoteProvider / book-derived explicit bid/ask'a taşımak + order payload/fill-confirm/error invariantlarını sağlamlaştırmak. **LIVE-BLOCKER** (canlı entry açılmadan ÖNCE şart).

**Anayasa:** live=0, NEW_ENTRIES_ENABLED=False, model/clamp/threshold/TP DEĞİŞMEZ. **Canlı emir gönderilmeyecek** (DRY_RUN + NEW_ENTRIES=False; testler mock/contract). Önce plan+onay, sonra TDD.

**Fiyat Anayasası (bu patch'e uygulanır):** API semantiği varsayılmaz; explicit bid/ask (AL→ask, SAT→bid); BUY/SELL kelimesine güvenilmez; mid/last yasak; her fiyatın kimliği (source/side/age/valid).

---

## 1. Dosya/satır bazlı değişiklik haritası
| Dosya:satır | Şu an (/price-ters) | Hedef |
|-------------|---------------------|-------|
| `execution/position_store.py:53` | `get_clob_price(token,"SELL")` (=ask, exit bid sanıyor) | `get_quote(token).bid` (SAT→bid) |
| `execution/clob_executor.py:218` | `_get_clob_price(token)` [BUY] (=bid, entry ask sanıyor) | `get_quote(token).ask` (AL→ask) |
| `main_loop.py:724` | `get_clob_price(yes_tid,"SELL")` (live YES mark exit) | `get_quote(yes_tid).bid` |
| `main_loop.py:735` | `get_clob_price(_no_tid,"SELL")` (live NO mark) | `get_quote(_no_tid).bid` |
| `main_loop.py:744` | `get_clob_price(yes_tid,"BUY")` (live YES entry-ref) | `get_quote(yes_tid).ask` |

## 2. BUY/SELL → explicit bid/ask
`get_clob_price(.,"BUY"|"SELL")` semantiği TERS ve YASAK. Tüm canlı fiyat alımları `get_quote(token)` → `.ask` (almak) / `.bid` (satmak). Side kelimesi yok; book-derived explicit.

## 3. Entry=ask, exit/mark=bid invariantları
- **Entry (clob_executor BUY):** limit/worst_price = `quote.ask + PRICE_PREMIUM` (taker fill buffer). ask = gerçek alış maliyeti.
- **Exit (position_store SELL):** fill/mark = `quote.bid` (gerçek satış geliri). exit limit = `quote.bid − PRICE_PREMIUM`.
- **Mark-to-market (main_loop monitor):** açık pozisyon değeri = `quote.bid` (likidite çıkış değeri).

## 4. API Contract Gate testleri
- `/price?side` TERS olduğu belgelenir (canlı 3/3 kanıt; regression doc-test).
- `get_quote` → /book-derived (best_ask=min asks, best_bid=max bids); side kelimesine bağlı DEĞİL.
- **Gate:** live execution'da `get_clob_price` import/kullanımı KALMADI (grep + inspect test). PASS olmadan patch yok.

## 5. Post-patch Price Lineage Audit tekrar kriteri
Patch sonrası live execution lineage: entry=ask, exit=bid, mark=bid → PASS. live=0 olduğu için runtime sample yok → **kod-seviyesi PASS + runtime PENDING** (canlı açılınca doğrulanır). Audit `get_clob_price` envanteri = 0 kritik yol.

## 6. Decision/live execution regression testleri
- Decision (scout) DEĞİŞMEZ (bu patch live-only). edge/fair testleri PASS.
- Live exit/entry fiyat seçimi: mock quote → entry ask, exit bid (yön doğruluğu).
- Full suite + mevcut clob_executor/position_store testleri PASS.

## 7. Latency etkisi
`get_quote` WS hit → 0 API; miss → 1 /book (eski 1 /price ≈ eşit). Live monitor cadence değişmez. scan_perf p90 raporlanır (≤ baseline×1.10).

## 8. Rollback planı
DB backup + git tag `pre-live-exec`. Kod revert (`git checkout`). live=0 olduğu için para riski yok. Kademeli: önce position_store+clob_executor, sonra main_loop monitor (her biri ayrı commit + test).

## 9. Live açmadan önce acceptance criteria
- [ ] live execution'da `get_clob_price` (kritik fiyat) = 0
- [ ] entry=ask, exit/mark=bid invariant (test)
- [ ] order payload invariant (§10) PASS
- [ ] execution error/unknown-state (§11) PASS
- [ ] fill kesin doğrulanmadan position AÇIK sayılmaz
- [ ] full suite + contract gate PASS · latency p90 ≤ sınır
- [ ] NEW_ENTRIES=False, live=0 korundu (bu patch canlı AÇMAZ)

## 10. Limit Price / Order Payload Invariant
**Mevcut (clob_executor:218+):** `create_market_order(MarketOrderArgs(side=BUY, amount=$, price=worst_price, order_type=FAK))`. worst_price = `live_ask + PRICE_PREMIUM`. live_ask = `_get_clob_price` (=bid, TERS).
- **Limit price kaynağı:** BUY entry → `quote.ask + PRICE_PREMIUM` (taker buffer). SELL exit → `quote.bid − PRICE_PREMIUM`. **quote.ask/bid book-derived, side-bağımsız.**
- **Taker/maker:** FAK = taker (mevcut derinlik dolar, kalan iptal). maker (askıda) YASAK.
- **Market order/slippage runaway:** `worst_price` slippage limiti = runaway koruması (price > worst_price fill olmaz). buffer = `PRICE_PREMIUM`.
- **Rounding/tick:** price `round(.,4)` (mevcut). Polymarket tick-size doğrulanacak (contract).
- **TIF / order type:** **FAK (Fill-And-Kill = IOC)** — askıda kalan emir YOK (kalan otomatik iptal). FOK kütüphane default → FAK override (mevcut, doğrulanacak). GTC YASAK (hanging).
- **Partial fill:** FAK kısmi kabul → fill miktarı response'tan okunacak; **kısmi fill → position shares = gerçek fill** (varsayılan amount DEĞİL). Partial → P&L NULL/gerçek-fill (paper pattern).
- **Taker slippage buffer:** limit = quote ± PRICE_PREMIUM (entry ask+buffer, exit bid−buffer). quote'a EŞİTLEME yok (fill garantisi için buffer).
- **Hanging/orphan cleanup:** FAK → askıda kalmaz (IOC). Yine de fill-confirm sonrası açık emir kontrolü (status poll).
- **Order payload contract testleri:** MarketOrderArgs(side, amount, price, FAK) → beklenen payload; price=quote-derived; FAK explicit; mock client ile.

## 11. Execution Error / Unknown State Handling
- **Network timeout:** order gönderildi mi belirsiz → **unknown_order_state** işaretle; OTOMATİK ikinci emir YASAK (duplicate riski).
- **4xx/5xx:** retry-edilebilir (timeout, 5xx geçici) vs fatal (signature/nonce/balance/allowance/insufficient_funds) sınıflandır. Fatal → retry YOK.
- **Response yok:** unknown_order_state → status polling (client_order_id ile).
- **Idempotency:** client_order_id / idempotency key (py_clob_client destekliyor mu doğrulanacak) → duplicate önleme.
- **Order accepted, fill yok:** status polling (N deneme, timeout) → fill kesinleşene kadar position AÇIK SAYILMAZ.
- **Timeout sonrası 2. emir:** YASAK.
- **Unknown state → kill-switch:** unknown_order_state tespitinde NEW_ENTRIES emergency pause tetiklenir (live emergency).
- **Rejection telemetry:** `execution_errors` tablosu (order_id, reason, retry_class, ts) — hangi reason ile yazılacak.
- **Exception contract/integration testleri:** timeout/4xx/5xx/no-response mock → unknown_order_state + no-duplicate + kill-switch tetik testi.

**KRİTİK INVARIANT:** Limit order gönderildikten sonra **fill sonucu kesin doğrulanmadan position AÇILMIŞ sayılmaz** (fill-confirm zorunlu; unknown → açık değil).

---

## En küçük güvenli patch (faz ayrımı)
- **Faz 1 (bu plan, fiyat yönü):** 5 `/price`-ters → `get_quote` (entry=ask, exit/mark=bid). Düşük risk, live=0. TDD + contract gate.
- **Faz 2 (order payload + error handling):** §10-11 (fill-confirm, unknown-state, idempotency, kill-switch, execution_errors tablosu). Daha büyük; canlı para yolunun çekirdeği. Faz 1 PASS sonrası, ayrı onay.
- **Faz 3:** canlı açma kararı (ayrı insan onayı; bu plan kapsamı DIŞI).

**Not:** Faz 1 fiyat-yönü düzeltmesi LIVE-BLOCKER'ı kaldırır (lineage temizlenir) ama Faz 2 (fill-confirm/error) tamamlanmadan canlı açılmamalı.
