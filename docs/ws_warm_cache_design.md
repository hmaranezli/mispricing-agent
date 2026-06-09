# Pre-Entry WS Warm Cache — Tasarım Dokümanı

> **Durum:** TASARIM. Kod YOK. Canlı entry/exit/stop/target/MIN_EDGE değişmez. `NEW_ENTRIES_ENABLED=False` korunur.
>
> **Tarih:** 2026-06-09 · İlgili: `data/ws_prices.py` (mevcut WS), REST timeout guard (commit sonrası)

## 0. Problem

Latency forensic'i gösterdi: 15m live scan latency'nin dominant kaynağı **REST fallback**, paper scan değil. Kök neden:
- WS price cache (`ws_prices._cache`) yalnızca `subscribe()` çağrılınca dolar.
- `subscribe()` yalnızca **pozisyon açılınca** çağrılır (main_loop.py).
- `NEW_ENTRIES_ENABLED=False` + 0 açık pozisyon → **0 subscription → WS cache boş → her scan tüm fiyatları REST'ten çeker**.
- Ölçüm: WS hit rate = **%0**, scan başına 4 REST fallback.

**Hedef:** Açık pozisyon olmasa bile tracked token'lara WS subscribe → cache sıcak → scan'ler REST yerine cache okur → latency düşer, 22s outlier riski azalır (REST timeout guard zaten eklendi, bu onu tamamlar).

## 1. Hangi token'lara subscribe?

Scout'un taradığı aktif kısa-vadeli market token'ları:
- Her scan cycle'da `find_shortterm(intervals=(5,15))` → aktif marketler → her birinin `clobTokenIds` (YES + NO).
- Tipik: ~10-16 aktif market × 2 token = **~20-32 token**.
- Önceliklendirme: `seconds_remaining > MIN_SECONDS` (canlı işlem adayı olabilecekler) önce; expired/çok-yeni pencereler atlanır.

## 2. Abonelik limiti

| Parametre | Öneri | Gerekçe |
|-----------|-------|---------|
| `MAX_WARM_SUBSCRIPTIONS` | 40 | ~16 market × 2 token + tampon; Polymarket WS makul yük |
| Limit aşımında | en yakın expiry'li token'ları düşür (LRU-by-expiry) | en alakalı pencereler sıcak kalır |
| Açık pozisyon token'ları | **her zaman öncelikli** (warm cache'ten bağımsız, mevcut subscribe korunur) | exit monitoring asla aç kalmaz |

## 3. RAM / cache TTL

- `ws_prices._cache[token]` = `{best_bid, best_ask, spread, ts}` (mevcut yapı).
- `STALE_SECS=15` (mevcut). Warm cache aynı TTL kullanır.
- RAM: 40 token × ~100 byte = ihmal edilebilir.
- **Unsubscribe lifecycle:** market expire olunca (seconds_remaining <= 0) token warm set'ten düşülür → cache temizlenir (memory leak önleme, 4h shadow/paper pattern'i gibi).

## 4. Stale price nasıl işaretlenir?

- Okuma anında `now - cache[token].ts > STALE_SECS` → **stale**.
- Stale ise: cache değeri **kullanılmaz**, REST fallback tetiklenir (mevcut davranış).
- Telemetri: `ws_warm_hit` / `ws_warm_stale` / `ws_rest_fallback` sayaçları `scan_audit`'e eklenir → warm cache etkinliği ölçülür.
- **Kritik:** Stale veri ASLA taze gibi kullanılmaz (anti-hallucination anayasa kuralı). Şüphede REST.

## 5. REST fallback nasıl azalır?

Akış (scout `_process_market`):
```
1. ws_prices.get_ask(token)  → warm cache HIT (taze) → REST YOK ✓
2. cache miss VEYA stale      → get_clob_price(token) REST (timeout 2s, guard'lı)
```
Mevcut kod zaten bu sıralamada (`_ws_prices.get_ask` → REST fallback). Tek eksik: cache'in **dolu** olması. Warm cache bunu sağlar → beklenen REST fallback %0 → ~%70-90 azalma (stale pencereler hariç).

## 6. Paper ve live scanner cache'i nasıl kullanır?

- **Değişiklik gerekmez** — ikisi de zaten `ws_prices.get_ask/get_bid` çağırıyor, REST fallback'li.
- Warm cache dolunca otomatik faydalanırlar (live scan_edges + paper scan_shadow_edges).
- `current_price` (HL) ayrı — bu WS değil HL REST; warm cache PM token'ları için. HL için ayrı bir warm mekanizma (out of scope, HL fiyatı 4 asset × cache zaten 5dk).

## 7. Failover: WS koparsa REST'e nasıl düşülür?

- `ws_prices._ws is None` veya bağlantı koptu → tüm okumalar otomatik REST fallback (mevcut davranış, değişmez).
- WS reconnect: mevcut `ws_prices.run()` reconnect loop'u warm subscription set'ini yeniden abone eder.
- **Fail-safe:** Warm cache bir optimizasyon katmanıdır; koparsa sistem REST ile (timeout guard'lı) çalışmaya devam eder. Hiçbir karar yalnızca warm cache'e bağlı değil.

## 8. Mimari (öneri, kod yok)

```
_ws_warm_loop (background, ayrı cadence ~30s):
    findings = await find_shortterm(intervals=(5,15))   # zaten cache'li (60s TTL)
    tokens = [tok for m in findings for tok in clobTokenIds(m)
              if seconds_remaining(m) > MIN_SECONDS][:MAX_WARM_SUBSCRIPTIONS]
    ws_prices.subscribe(tokens - already_subscribed)
    ws_prices.unsubscribe(warm_subscribed - tokens - open_position_tokens)  # expire temizliği
```
- Ayrı task (4h shadow / paper scan pattern'i), live 7s loop'u yavaşlatmaz.
- `subscribe`/`unsubscribe` mevcut `ws_prices` API'si (yeni WS kodu gerekmez, sadece çağrı).
- Açık pozisyon token'ları unsubscribe'dan **muaf** (exit monitoring korunur).

## 9. Riskler / unknown

- **unknown:** Polymarket WS 40 eşzamanlı subscription'ı stabil taşır mı (rate limit / disconnect)? İlk denemede 20 ile başla, izle.
- **unknown:** Warm cache hit rate gerçekte ne olur — `ws_warm_hit` telemetrisi ile ölçülecek.
- WS subscription churn (her 30s market değişimi) reconnect tetiklerse ek yük; subscribe/unsubscribe diff minimal tutulmalı (sadece değişenler).
- Bu tasarım **latency optimizasyonu**; REST timeout guard (eklendi) zaten 22s outlier'ı keser. Warm cache "ortalama" latency'yi düşürür.

## 10. Başarı kriteri

- `scan_audit` `ws_warm_hit` oranı > %70 (stale hariç).
- 15m live scan p50 latency < 1s (mevcut ~1.8s'den).
- REST fallback sayısı scan başına < 1 (mevcut 4).

## Özet Karar

| Soru | Cevap |
|------|-------|
| Yeni WS kodu? | Hayır — mevcut `ws_prices.subscribe/unsubscribe` kullanılır |
| Yeni katman | `_ws_warm_loop` background task (ayrı cadence) |
| Subscribe kapsamı | aktif kısa-vadeli market token'ları, MAX 40 (20 ile başla) |
| Failover | WS koparsa REST (timeout guard'lı) — mevcut davranış |
| Risk | WS subscription stabilitesi (unknown, telemetri ile ölçülecek) |
| Önkoşul | REST timeout guard (✅ eklendi) bu tasarımı tamamlar |

---

## 11. Implementation Checklist (kod yok — sadece plan)

> **ÖN-BLOKER:** `get_book` asks/bids sıralama bug'ı (bkz 3-saat forensik raporu) ÖNCE düzeltilmeli. Warm cache de aynı book parse'ını kullanacağı için bug warm cache'e taşınır. Sıra: **book-order fix → paper revalidation → WS warm cache**.

**Hangi modüller değişecek:**
- `data/ws_prices.py` — subscribe/unsubscribe zaten var; değişiklik gerekmez (sadece çağrılır).
- `main_loop.py` — yeni `_ws_warm_loop` background task + feature flag kontrolü.
- `config.py` — yeni flag `WS_WARM_CACHE_ENABLED=False` (default KAPALI) + `MAX_WARM_SUBSCRIPTIONS=20`.
- `council/scout.py` — değişiklik gerekmez (zaten `ws_prices.get_ask` → REST fallback).

**Hangi testler yazılacak (TDD):**
- `_ws_warm_loop` token seçimi: aktif market token'ları, MIN_SECONDS filtresi, MAX limit cap.
- subscribe/unsubscribe diff: sadece değişen token'lar (churn minimize).
- expire temizliği: market expire → unsubscribe → cache temizlenir (memory leak yok).
- açık pozisyon token'ları unsubscribe'dan muaf.
- stale okuma → REST fallback (cache STALE_SECS aşımı).
- WS kopması → REST fallback (failover), exception loop'u öldürmez.
- feature flag KAPALI → warm loop hiç çalışmaz (canlı davranış değişmez).
- telemetri: `ws_warm_hit`/`ws_warm_stale`/`ws_rest_fallback` sayaçları.

**Feature flag ile default-kapalı ekleme:**
- `config.WS_WARM_CACHE_ENABLED=False` → `_ws_warm_loop` task hiç başlatılmaz.
- True olunca yalnızca warm subscription eklenir; okuma path'i (get_ask/get_bid) zaten cache-then-REST, değişmez.

**İlk fazda sadece paper scanner mı?**
- Evet. Flag açıldığında ilk faz: warm cache **paper scan'i** hızlandırır (live scan zaten REST fallback'li çalışıyor, bozulmaz).
- Telemetri ile `ws_warm_hit` oranı ve fiyat tutarlılığı (warm cache ask vs REST ask farkı) ölçülür — **shadow-read mode**.

**WS cache shadow-read mode:**
- Warm cache okunur AMA karar yine REST ile doğrulanır (ilk fazda): her warm hit'te paralel REST çekilip `warm_ask vs rest_ask` farkı loglanır. Fark eşik altındaysa (örn <1¢) warm güvenilir kabul edilir.
- Bu, warm cache'i "körlemesine güven" yerine "kanıtla sonra güven" yapar (anti-hallucination).

**Live scanner ne zaman kullanacak:**
- Geçiş kriterleri (hepsi geçmeli): `ws_warm_hit` > %70 · warm-vs-REST fiyat farkı p95 < 1¢ · WS disconnect oranı < %5/saat · 24h shadow-read stabil.
- Geçince live scan `ws_prices.get_ask` warm cache'ten okur (kod zaten hazır), REST yalnızca stale/miss'te.

**Rollback planı:**
- `WS_WARM_CACHE_ENABLED=False` → anında eski davranış (REST fallback). Tek satır, restart ile.
- Warm cache hiçbir kararı tek başına belirlemediği için (her zaman REST fallback var) rollback risksiz.

**Cache stale/TTL/fallback testleri:**
- ts > STALE_SECS → stale → REST.
- WS None → REST.
- token cache'te yok → REST.
- warm hit taze → REST YOK (hit sayacı artar).

---

## 12. KRİTİK ÖN-BLOKER: get_book sıralama bug'ı

3-saat forensik (2026-06-09) ortaya çıkardı: `data/clob_price.get_book` docstring "asks: artan, asks[0]=en iyi ask" diyor AMA gerçek Polymarket `/book` yanıtında `asks[0]={'price':'0.99'}` (en yüksek/en kötü), gerçek best ask `get_clob_price=0.16`. n_asks=83.

**Etkilenen kod (hepsi asks[0]/bids[0]'ı "best" sanıyor):**
- `execution/paper_tracker._estimate_entry_price` → paper entry hep 0.99 (en pahalı) → net_ev sahte negatif
- `data/depth_enricher` → entry depth slippage telemetri yanlış
- `execution/air_pocket_shadow._worker` → post-wait bid yanlış
- `data/shadow_quote._read_book` → shadow ask yanlış

**Doğru parse:** ask için en iyi = `min(price)` (asks azalan sıralıysa `asks[-1]`); bid için en iyi = `max(price)`. Depth-walk en iyiden başlayıp uzaklaşmalı.

**Öncelik:** Bu bug paper lab'in TÜM net_ev/slippage çıktısını geçersiz kılıyor. WS warm cache ÖNCESİ düzeltilmeli + paper veri yeniden toplanmalı.
