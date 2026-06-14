# F1a — PM Up/Down resolution rule source

> **PM Up/Down resolution rule source** capture kapısı. F1 data fidelity audit'inin
> `resolution-source/index` blocker'ını daraltır/çözer. **offline data only** stance; tek istisna:
> aşağıda kayıtlı, insan-onaylı, unauthenticated tek public read. Tarih: 2026-06-14.

## 1. Verdict

- **VERDICT = SOURCE-RESOLVED / DATA FIDELITY CONFOUNDER CONFIRMED.**
- Üst denetim: **Poly API data fidelity** (F1) `resolution-source/index` blocker'ı — bu artifact onu
  BTC 15m için çözer, ama yeni bir besleme confounder'ı açar.
- BTC 15m örnek market'i için exact resolution source + rule + edge-case YAKALANDI (§2/§3).
- **YENİ BLOCKER:** bot `fair_value` **Hyperliquid mark/mid** kullanıyor, PM ise **Chainlink BTC/USD**
  ile resolve ediyor → **HL ≠ Chainlink kaynak uyuşmazlığı = DOĞRULANMIŞ data fidelity confounder** (§5).
- Bu yüzden veri besleme HÂLÂ **DATA FIDELITY NOT VERIFIED** (kaynak bulundu ama besleme YANLIŞ kaynağı
  kullanıyor); diğer asset/interval'lar için kural metni hâlâ **BLOCKED-UNTIL-DOCS** (§4).
  `production canary NOT approved`.

## 2. Captured evidence (insan-onaylı tek public read)

- **Fetched slug:** `btc-updown-15m-1781455500` (repo `slugs_for_now`, BTC 15m, güncel pencere).
- **Endpoint:** unauthenticated public **Gamma markets/events by slug** — `/markets?slug=<slug>`
  (auth header yok, API key yok, order/trade/balance yok). HTTP 200, 1 sonuç.
- **resolutionSource (resolution source):** `https://data.chain.link/streams/btc-usd`.
- **source/index:** **Chainlink BTC/USD data stream**.
- **timestamp rule:** Bitcoin fiyatı **time range SONU** vs **time range BAŞI** karşılaştırılır
  (başı = `eventStartTime/startDate`, sonu = `endDate`).
- **edge cases:** **greater than or equal ⇒ Up**; aksi halde **Down**.
- Mevcut rule-ilgili alanlar: `resolutionSource`, `description` (513 char), `umaResolutionStatuses`
  (boş `[]` — henüz UMA'ya gitmemiş aktif market).

## 3. Rule text (description özeti)

> "resolve to **Up** if the Bitcoin price at the **end** of the time range … is **greater than or
> equal to** the price at the **beginning** of that range. Otherwise … **Down**. The resolution source
> … is **Chainlink, BTC/USD data stream** (https://data.chain.link/streams/btc-usd)…"

(Not: description'ın son ~113 karakterlik kuyruğu raporlama sırasında ekrana kesik basıldı; tam-verbatim
kayıt istenirse onaylı ikinci read gerekir. Core source+rule+edge-case yukarıda tamdır.)

## 4. Scope limit — bir örnek tüm evreni çözmez

- Bu read **yalnız BTC 15m** market'inin source/pattern'ini kanıtlar. **Diğer asset/interval'lar
  (eth/sol/xrp × 5m/15m/4h) için kural metni HENÜZ kaydedilmedi** → onlar için
  **BLOCKED-UNTIL-DOCS** sürer (per-asset Chainlink stream farklı olabilir: eth-usd/sol-usd/xrp-usd;
  varsayım ÇIKARILMAZ — **do not infer index from generic docs** / tek örnekten genelleme yok).
- Genel docs zaten: marketler **UMA Optimistic Oracle** ile resolve; **per-market resolution rules**
  (**resolution source** + **end date** + **edge cases**). Spesifik index ancak per-market read ile
  doğrulanır.

## 5. Confirmed confounder — fair-vs-realized

- **fair-vs-realized confounder DOĞRULANDI:** `data/fair_value.py::fair_yes(p_now, p_ref, …)` girdi
  olarak **Hyperliquid** mid/mark alıyor (`data/hyperliquid.py`), ama PM **Chainlink BTC/USD stream**
  ile resolve ediyor. İki kaynak arasındaki basis/latency → model overconfidence GİBİ görünen
  sistematik sapma (recorded Brier 0.39 / fair-67-vs-win-14) **veri kaynağı uyuşmazlığı** olabilir.
- Ek: p_ref pencere **başına** (start), p_now pencere **sonuna** (end) **Chainlink** fiyatına anchor'lı
  olmalı — HL anlık değil.

## 6. Next remediation (calibration'dan ÖNCE)

1. **Chainlink-aligned price source** entegrasyonu VEYA explicit **HL↔Chainlink basis validation**
   (offline: kayıtlı HL serisi vs Chainlink BTC/USD; sistematik fark/latency ölç).
2. Diğer asset/interval source capture (eth/sol/xrp; per-asset Chainlink stream).
3. p_ref start-anchor + window timestamp doğrulaması.
4. Ancak bunlar netleşince → offline **calibration metrics** (Brier/reliability) anlamlı olur.

## 7. Live/API NO-GO confirmation

- **no live API** (trading/auth), no Telegram, no live DB; `D#7 phase-2 balance/auth probe not run`;
  `production canary NOT approved`. §2'deki tek read insan-onaylı, unauthenticated, no-trade public
  Gamma idi; başka fetch yapılmadı. Ek read/entegrasyon yalnız insanın açık komutuyla.
