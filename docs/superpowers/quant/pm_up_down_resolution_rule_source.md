# F1a — PM Up/Down resolution rule source

> **PM Up/Down resolution rule source** capture kapısı. F1 data fidelity audit'inin
> `resolution-source/index` blocker'ını daraltır. Amaç: repo'nun hedeflediği spesifik Up/Down crypto
> market'lerinin TAM çözüm kuralını (resolution source / index / timestamp / edge cases) repo'ya
> KAYDETMEK. **offline data only · no live API.** Tarih: 2026-06-14.

## 1. Verdict

- **VERDICT = BLOCKED-UNTIL-DOCS / DATA FIDELITY NOT VERIFIED.** PASS YOK.
- Exact Up/Down `resolution-source/index` repo/local docs'ta KAYITLI DEĞİL; spesifik per-market/event
  rule metni kaydedilene kadar bloklu. Bu, F1'in `Poly API data fidelity` blocker'ını ve üst seviye
  edge correctness BLOCKED durumunu destekler. `production canary NOT approved`.

## 2. Targeted market inventory (repo'dan, kanıtlı)

- Slug builder `data/shortterm.py:78 slugs_for_now` → **`{asset}-updown-{interval}m-{ts}`**;
  `data/shortterm.py:141 slugs_for_now_4h` → **`{asset}-updown-4h-{ts}`**.
- Evren: **btc / eth / sol / xrp** × **5m / 15m / 4h**. `ts = (now // (interval*60)) * (interval*60)`
  (interval'e hizalı epoch). Örnek: `btc-updown-15m-1718000000`.
- Lookup: `_fetch_slug` → **Gamma markets/events by slug** (`params={"slug": slug}`).

## 3. What the repo parses (and does NOT)

- Parse edilen: `slug`, `endDate` / `eventStartTime` / `startDate` (→ `seconds_remaining`),
  `clobTokenIds` (`_parse_token_ids` → asset_id). [`parse_market_window`]
- **Parse/kayıt EDİLMEYEN:** resolution rule / **resolution source** / index / `umaResolutionStatus` /
  `description` / clarification / edge-case metni. (grep: data/ + council/ → YOK.) Yani repo market'in
  NASIL resolve olduğunu hiç görmüyor — yalnız pencere + token.

## 4. General official docs basis (yalnız genel kanıt)

- Polymarket Resolution docs: marketler **UMA Optimistic Oracle** ile resolve olur; her market'in
  **per-market resolution rules** vardır — **resolution source**, **end date**, **edge cases**; kuralı
  "title" değil bu metin belirler.
- Polymarket Fetching Markets docs: market/event verisi **Gamma markets/events by slug** ile çekilir
  (`/events`, `/markets`; active/closed filtre, pagination).
- **Bunlar GENEL.** Bizim spesifik crypto Up/Down market'in hangi fiyat index'i / hangi timestamp /
  hangi snapshot ile resolve olduğunu SÖYLEMEZ.

## 5. Why generic docs cannot unblock (do not infer index from generic docs)

- **do not infer index from generic docs:** Genel "UMA + per-market rules" ifadesinden spesifik
  index/timestamp ÇIKARILAMAZ. Çıkarım yapmak = uydurma = anayasa madde 3 ihlali. Bu yüzden
  `resolution-source/index` BLOCKED kalır; varsayımla doldurulmaz.

## 6. fair-vs-realized confounder linkage

- **fair-vs-realized confounder:** `fair_value` p_now = HL mid/mark. PM resolve index'i HL mark'tan
  farklıysa, recorded Brier 0.39 / fair-67-vs-win-14 sapması model overconfidence DEĞİL **veri basis'i**
  olabilir. Bu kural metni kaydedilip HL↔PM index eşleşmesi doğrulanmadan kalibrasyon yanıltıcıdır →
  F1a, calibration metriklerinin ÖN-koşuludur.

## 7. Exact source required before GREEN-PASS

GREEN-PASS (data fidelity VERIFIED) için kaydedilmesi gereken kesin kaynak:
1. Hedef market/event'in resmi resolution rule metni: **resolution source** (hangi index/oracle),
   **timestamp/snapshot** kuralı, **edge cases** (tie / veri-yok / gecikme).
2. Tercih edilen yol (insan onayı gerekir): (a) **public Gamma markets/events by slug** yanıtındaki
   rule/description alanının ham kaydı; veya (b) docs.polymarket.com ilgili market rule sayfasının ham
   metni (paste). İkisi de offline-first; canlı trading/auth YOK.

## 8. Live/API NO-GO confirmation

- **no live API**, no Telegram, no live DB; `D#7 phase-2 balance/auth probe not run`;
  `production canary NOT approved`. Exact rule capture için public Gamma fetch / web-docs onayı
  AYRI ve insanın açık komutuyla.
