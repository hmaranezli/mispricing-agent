# F1 — Poly API Data Fidelity & Usage Audit

> **Pre-F money-making audit** alt-denetimi. Bu artifact, sahte edge'in model matematiğinden DEĞİL,
> veri besleme / API semantiğinden gelip gelmediğini OFFLINE inceler (**garbage-in garbage-out**).
> **offline data only** · **no live API** · `D#7 phase-2 balance/auth probe not run`. Tarih: 2026-06-14.

## 1. Scope and verdict

- **VERDICT = BLOCKED-UNTIL-DOCS / DATA FIDELITY NOT VERIFIED.** PASS VERİLMEDİ.
- Bu, üst seviye `FAIL/BLOCKED on edge correctness` verdict'ini destekler: edge correctness, veri
  besleme doğruluğu (`data ingestion correctness`) kanıtlanmadan değerlendirilemez.
- `production canary NOT approved` korunur; canlı kapı kilitli.
- Kapsam: Polymarket Gamma/CLOB + Hyperliquid besleme `API usage audit` (offline repo semantiği +
  kullanıcının sağladığı resmi docs index'i). Exact per-market kuralı repo'da YOKSA → BLOCKED.

## 2. Official docs/source basis supplied

Kullanıcı tarafından sağlanan resmi docs bağlamı (repo'ya ham metin İŞLENMEDİ — yalnız işaret):
- `https://docs.polymarket.com/` — Core Concepts, Market Data, Trading, API Reference, WebSocket,
  Resources, OpenAPI specs içerir.
- **Resolution docs:** her market'in önceden tanımlı çözüm kuralı vardır — resolution source, end
  date, edge cases; trade öncesi okunmalıdır.
- **Fetching Markets docs:** Gamma API event/market lookup (slug, active/closed filtre, pagination,
  event-based discovery).
- **Kısıt:** Genel docs'tan **spesifik Up/Down crypto resolution index'i UYDURULMADI.** Exact
  per-market rule/source metni repo/local docs'ta olmadığından `resolution-source/index` =
  **BLOCKED-UNTIL-DOCS** (§9).

## 3. Repo usage inventory

- **Polymarket Gamma:** `data/polymarket.py::fetch_crypto_markets` (`gamma-api.polymarket.com/markets`),
  `data/shortterm.py` (`fetch_by_slug`, `fetch_resolved`, `parse_market_window`, `_parse_token_ids`).
- **Polymarket CLOB:** `data/clob_price.py::get_quote` (book-derived), `data/ws_prices.py` (WS asset
  price), `data/clob_live_adapter.py` (ARAF trade şeması — closeout §8 ile kalibre).
- **Hyperliquid (kıyas kaynağı):** `data/hyperliquid.py::fetch_market_state` (`api.hyperliquid.xyz/info`
  → `midPx/markPx/oraclePx/funding/prevDayPx`), `data/hl_candles.py` (geçmiş candle).
- **Olasılık:** `data/fair_value.py::fair_yes(p_now, p_ref, seconds_remaining, sigma)` =
  Φ(log(p_now/p_ref)/(σ√T)).
- Tüm HTTP `aiohttp`, timeout'lu. `aggregation rules` (candle interval, mid vs mark vs oracle) ve
  `fee/slippage compatibility` (fee_rate.py vs gerçek CLOB taker fee) ayrıca doğrulanmalı.

## 4. Polymarket vs Polygon.io naming disambiguation

- **Polymarket vs Polygon.io:** Repo taraması yalnız **Polymarket** (Gamma `gamma-api.polymarket.com`,
  CLOB, `py_clob_client_v2`) + **Hyperliquid** (`api.hyperliquid.xyz`) kullanıyor. **Polygon.io
  kullanımı YOK.**
- Dolayısıyla Polygon.io'ya özgü kaygılar (SIP feed, `condition/status codes` borsa kodları,
  `adjusted/unadjusted data` split/dividend) **mevcut kod yoluna UYGULANMAZ (not applicable).**
- **Not:** Gelecekte herhangi bir Polygon.io bağımlılığı eklenirse AYRI bir data fidelity audit
  gerekir (özellikle adjusted/unadjusted ve SIP latency).

## 5. Market identity assumptions

- `market/query semantics`: market_token_id = `clobTokenIds[0|1]` = CLOB `asset_id` (outcome token);
  `conditionId` AYRI (ARAF'ta doğrulandı, YÜKSEK güven). Gamma `id`/`conditionId`/`slug` ile lookup.
- `condition/status codes`: Gamma market active/closed/resolved durumu + `fetch_resolved` semantiği —
  durum kodlarının (resolved vs closed-unresolved) tam eşlemi doğrulanmalı; yanlış status → erken/yanlış
  resolve okuması.

## 6. Timestamp/window/latency assumptions

- `timestamp/latency assumptions`: `parse_market_window` → `seconds_remaining = endDate − now(local UTC)`;
  start = `eventStartTime/startDate`. **Riskler:** (a) local clock drift; (b) endDate timezone parse
  doğruluğu; (c) **HL `p_now` fetch'i ile PM penceresi arasındaki latency** → p_now ve pencere
  senkronize değil; (d) p_ref'in pencere AÇILIŞINA (start) snap edilip edilmediği — scan anına
  anchor'lanırsa sistematik bias.

## 7. Price-source mismatch risks

- **EN KRİTİK confounder:** `fair_value` `p_now` = HL `mid/mark`, `p_ref` = referans. Ama PM Up/Down
  market'i **kendi resolution source'una** göre resolve olur (Chainlink/oracle/belirli borsa index'i,
  belirli timestamp). HL `mark` ile PM'in resolve ettiği index FARKLIYSA → **sistematik basis → sahte
  edge** (`garbage-in garbage-out`). HL'de bile mid/mark/oracle üçü farklı; PM hangisine denk belirsiz.
- Bu, recorded `Brier 0.39 > random` / `fair %67 vs win %14` sonucunu model-suçu OLMADAN açıklayabilir.

## 8. Adjusted/unadjusted and stale/missing data risks

- `adjusted/unadjusted data`: HL perp fiyatları (mark/prevDay) funding-adjusted mı — doğrulanmadı
  (perp genelde unadjusted ama teyit gerek). Crypto'da split/dividend yok → klasik adjusted sorunu
  düşük, ama funding/index-vs-mark farkı geçerli.
- `stale/missing data handling`: `data/hyperliquid.py` `float(ctx.get("midPx") or 0)` → **eksik/stale
  fiyat → 0**. fair_value p≤0'da raise eder (kısmi koruma) ama `_signal` ve diğer yollar 0-fiyatla
  yanlış sinyal üretebilir. Stale-but-nonzero (güncellenmemiş ama 0 değil) fiyat sessizce sahte edge
  besler — timestamp/staleness guard'ı yok.

## 9. Resolution-source/index blocker

- `resolution-source/index` = **BLOCKED-UNTIL-DOCS.** PM Up/Down crypto market'in TAM çözüm kaynağı
  (hangi index/oracle, hangi timestamp/snapshot, tie/edge-case kuralı) repo/local docs'ta KAYITLI
  DEĞİL. Resmi per-market resolution rule/source metni kaydedilene kadar `DATA FIDELITY NOT VERIFIED`.
- GREEN için gereken: ilgili market'lerin resmi resolution rule metni (source + timestamp + aggregation)
  repo'ya kaydedilmeli; veya açık web-docs çekme onayı.

## 10. Fair-vs-realized confounder before calibration

- `fair-vs-realized confounder`: Bu data-fidelity audit **calibration metriklerinden ÖNCE** gelmelidir.
  Eğer p_now/p_ref/index/timestamp yanlışsa, fair-vs-realized sapması (Brier) **model overconfidence
  DEĞİL veri basis'i** olabilir. σ recalibrate etmek yanlış-index basis'i düzeltmez — sağlam modeli
  kirli veriyle yeniden eğitip aynı duvara çarparız. Confounder izole edilmeden kalibrasyon yanıltıcı.

## 11. Required next evidence

1. PM Up/Down resolution rule/source metnini repo'ya kaydet (resolution-source/index blocker'ı çöz).
2. HL price-source ↔ PM resolution-index eşleşmesini doğrula (hangi fiyat = resolve fiyatı).
3. p_ref'in pencere açılışına (start) snap'lendiğini + HL/PM latency penceresini ölç.
4. Stale/missing guard (midPx==0 / timestamp-stale reddi) ekle — ayrı TDD.
5. `fee/slippage compatibility`: fee_rate.py vs gerçek CLOB taker fee uyumu.
6. Ancak bunlar netleşince → offline calibration metrics artifact (Brier/reliability).

## 12. Live/API NO-GO confirmation

- `no live API`, no Telegram, no live DB; `D#7 phase-2 balance/auth probe not run`;
  `production canary NOT approved`. Canlı API çekimi/probe yalnız insanın açık yazılı onayıyla.
