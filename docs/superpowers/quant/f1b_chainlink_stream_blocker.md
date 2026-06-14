# F1b — Real HL↔Chainlink Basis Measurement Blocker

> **F1b Measurement BLOCKED.** F1a, PM Up/Down'ın Chainlink BTC/USD **Data Streams**
> (`data.chain.link/streams/btc-usd`) ile resolve olduğunu kanıtladı ve HL≠Chainlink confounder'ını
> işaretledi. F1b'nin GERÇEK ölçümü, exact Data Streams verisi olmadan yapılamaz. **offline data only ·
> no live API.** Tarih: 2026-06-14.

## 1. Verdict

- **F1b Measurement BLOCKED.** `analysis/source_basis.py` araç-takımı (directional_disagreement_rate,
  source_basis_bps_stats, directional_disagreement_rate_with_shift) hazır AMA gerçek HL↔Chainlink
  **Data Streams** serisiyle beslenemez → confounder büyüklüğü ölçülemez. PASS YOK.

## 2. Data Streams vs Data Feeds (DEĞİŞTİRİLEMEZ / non-interchangeable)

İki AYRI Chainlink ürünü — biri diğerinin yerine kullanılamaz:

1. **Chainlink Data Streams** — **PM resolution source** (`data.chain.link/streams/btc-usd`).
   **tick/pull-based, low-latency**, yüksek zaman çözünürlüğü. **Authentication required for Streams**
   (API key ile korunuyor) → "no auth" altında public unauthenticated çekilemez.
2. **Chainlink Data Feeds** — on-chain aggregator (RPC `eth_call`), public unauthenticated.
   **heartbeat/deviation push-based** (örn. saatlik heartbeat veya ~%0.5 sapma eşiği ile güncellenir)
   → güncellemeler arası fiyat **stale** kalabilir. Bu PM'in resolve ettiği kaynak DEĞİLDİR (proxy).

## 3. Mathematical blocker — Time Resolution Mismatch

- **Time Resolution Mismatch** (**Heartbeat/Deviation vs Tick/Pull**): `source_basis` shift testleri
  **0s / 30s / 60s** ölçeğinde çalışır. Data Feed'in heartbeat/deviation örneklemesi bu ölçek için
  ÇOK KABA — Feed o 30–60 saniyelik aralıkta hiç güncellenmemiş olabilir.
- Sonuç: Feed-proxy ile yapılan bir ölçüm, gerçek HL↔PM-Stream **kaynak basis'ini DEĞİL**,
  **temporal heartbeat noise** ve **stale price confounder**'ı ölçer. Yani ölçülen değişken yanlış
  olur (Feed'in güncellenmemişliği, kaynak farkı gibi görünür).
- **Bu yüzden Feed-proxy F1b'yi TEMİZLEYEMEZ.** directional_disagreement_rate_with_shift'in 30s/60s
  sonuçları Feed verisiyle anlamsızdır; yalnız Stream'in tick/pull çözünürlüğünde anlamlıdır.

## 4. Allowed paths

**Allowed paths: exact Streams auth, explicit manual CSV/JSON paste, explicitly-labeled Feed-proxy smoke test cannot clear F1b.** Açık:
1. **exact Chainlink Data Streams** read-only authenticated erişim (ayrı, açık insan onayı + scope;
   "no auth" kısıtını aşar — bu artifact onu açmaz).
2. **explicit manual Streams CSV/JSON paste** — operatör data.chain.link Streams BTC/USD time-series'i
   elle verir → offline, fetch'siz; eşleşen HL serisiyle ölçülür. (En temiz, fetch-riski yok.)
3. **explicitly-labeled Feed-proxy smoke test** — yalnız "smoke" etiketiyle, basis büyüklüğü için kaba
   bir üst-sınır sezgisi olarak; **F1b'yi CLEAR ETMEZ** (§3 gereği matematiksel olarak geçersiz).

## 5. Scope / what remains

- F1b ölçümü BLOCKED kalır; calibration metrics bu çözülmeden anlamlı değil (HL↔Stream basis bilinmeden
  fair-vs-realized confounder ayrıştırılamaz).
- HL tarafı (public unauthenticated `candleSnapshot`) her zaman hazır; eksik olan yalnız exact Stream
  serisi.
- **no live API**, no Chainlink/HL fetch bu turda; **offline data only**. Üretim trading kodu
  (fair_value/hyperliquid/main_loop/monitor) ve `analysis/source_basis.py` DEĞİŞMEDİ.
