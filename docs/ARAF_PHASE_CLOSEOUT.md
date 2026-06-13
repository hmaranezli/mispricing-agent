# ARAF Pure Reconcile Fazı — SEALED CLOSEOUT

> Kalıcı handoff. Yeni oturum BU dosyayı okur, sonra git sanity, sonra insana sorar. Tahmin/uydurma
> ile ilerlemez (CLAUDE.md anayasa madde 1 + 3). Bu dosya ARAF **pure reconcile** fazının kapanışıdır.

## Durum: SEALED

- **Seal commit:** `f101eac97d28b1ed306e0fdafaf65e243b4a3e17` — **HEAD == origin/master** (sync 0/0).
- **Seal checkpoint:** `tests/test_reconciliation.py` **9 passed** + `tests/test_clob_reconcile.py` **24 passed**
  = **33 passed**. Warnings / ResourceWarning yok. Canlı DB/API kullanılmadı (saf fixture, I/O-free).
- **Final checkpoint komutu (yeniden doğrulama):**
  ```
  python -m pytest tests/test_reconciliation.py tests/test_clob_reconcile.py -v
  ```
  Beklenen: 33 passed. (Geniş blanket `tests/` bilinçli koşulmaz: `test_main_loop.py`/`test_hl_candles.py`
  network'e asılır, bazı dosyalar process-exit'te aiosqlite teardown RC=124 → test başarısızlığı DEĞİL.)

## 1. Tamamlanan invariant'lar (pure resolver — `data/clob_reconcile.py`)

Tümü RED → GREEN → micro-checkpoint → scoped-commit disipliniyle, Decimal-only (float yok), keyfi
quantize yok, fail-closed, anti-hallucination (CONFIRMED kanıt olmadan terminal muhasebe yok):

1. **Dual-oracle no-terminal guard** — get_order=lifecycle, get_trades=settlement. CONFIRMED trade
   kanıtı olmadan FILLED/PARTIAL_FILLED/CANCELLED YAZILMAZ; MATCHED / size_matched>0 tek başına yetmez.
2. **Zero-fill stability** — CANCELLED yalnız İKİ stabil canonical zero-fill-cancel gözleminde; tek
   gözlemde terminal yazılmaz. 6 safety-matrix guard (unconfirmed-trace block, scan-complete `LTE=`,
   size_matched>0, observation-mismatch, order_id-mismatch, invalid-numeric fail-closed).
3. **Residual-live fail-closed** — `0 < filled < target` VE order canonical LIVE/MATCHED → terminal
   DEĞİL → `RECOVERY_REQUIRED` (PARTIAL_FILLED ∈ TERMINAL_STATES donmasından korunur; FAK invariant breach).
4. **Dead-residual partial** — `filled < target` VE order canonical CANCELED → terminal `PARTIAL_FILLED`.
5. **Taker/maker accounting evidence** — taker top-level alanlardan; maker nested `maker_orders[]` slottan
   (top-level POISON kör kullanılmaz). matched_size / avg_price / fee_rate_bps / matched_trade_ids /
   accounting_source="CONFIRMED_TRADE".
6. **Taker/maker VWAP aggregation** — çok trade'de `matched_size=Σ`, `avg_price=Σ(size·price)/Σsize`,
   `matched_trade_ids` data-order; full-fill + dead-residual partial yollarında.
7. **Mixed-fee fee_rate_bps None policy** — tüm fill'ler aynı parseable rate ise o Decimal; farklı/eksik
   → `None` (blend/weight YOK). PIN ile kilitli.
8. **Taker/maker identical dedup** — aynı scan payload'ı içinde BİREBİR AYNI satır (full identity) tekrar
   görünürse (pagination overlap yankısı) bir kez sayılır.
9. **Taker/maker conflicting-duplicate fail-closed** — aynı trade.id (maker: + slot.order_id) FARKLI
   payload → ortak `_ACCOUNTING_CONFLICT` sentinel → `RECOVERY_REQUIRED`, accounting None, exception YOK.
   Sessiz skip/seçim/sum/VWAP yasak (heuristic tahmin = veri bozulması).

Saf: I/O / network / DB yok; tüm kararlar **fixture-contract v0** üzerinde (canlı şema doğrulanana kadar
alan adları/tipleri/enum'lar VARSAYIM).

## 2. DB double-run idempotency — Task H'de SEALED (bağımsız)

- `execution/order_intent.py::confirm_fill_atomic` — `BEGIN IMMEDIATE` + app-level precheck
  (`SELECT 1 FROM positions WHERE order_intent_id=?` → "DUPLICATE") + tek-transaction INSERT+UPDATE +
  IntegrityError ROLLBACK+readback. Döner `"OPENED"|"DUPLICATE"`.
- `db/schema.py` — partial UNIQUE index `ix_positions_order_intent_id ON positions(order_intent_id)
  WHERE order_intent_id IS NOT NULL` (Task H1 duplicate accounting guard).
- Testler: `tests/test_task_h_fill_confirm.py` H3-3 (double-confirm → DUPLICATE no-op, readback-proof),
  H3-4 (IntegrityError+readback-existing → DUPLICATE), H3-5 (readback-missing → re-raise, fail-closed),
  + insert/update rollback atomicity. (3 hedef test doğrulandı: PASSED.)
- İdempotency key = **`order_intent_id`** (one intent → one position; FAK one-shot modeli).

## 3. B2 — Per-trade settlement ledger KARARI

- **Blocker DEĞİL.** Korektlik (çift position open engeli) `order_intent_id` idempotency ile zaten
  sağlanıyor (Task H). Bot ledger olmadan doğru paper/live yapar.
- **Ops/audit enhancement.** Değeri: per-trade forensic lineage + cross-intent defense-in-depth dedup.
- **Live-schema-gated backlog.** Kolon seti + maker multi-slot discriminator canlı get_trades örneğine
  bağlı (madde 3 — şema uydurma yok). incremental-settlement gerekçesi FAK'ta normal yol değil
  (residual-live → RECOVERY).

## 4. B2 backlog notu

- **Amaç:** matched_trade_ids'i trade-granül, idempotent `settlement_trades` tablosuna yaz → forensic
  lineage + cross-intent defense-in-depth dedup.
- **v0 anahtar varsayımı:** UNIQUE `(order_intent_id, trade_id)` + `fill_role` (taker/maker);
  "≤1 katkı per (intent,trade)" (pure resolver "trade başına ≤1 maker slot" varsayımıyla simetrik).
- **Maker multi-slot discriminator:** aynı trade'de bizim order_id'mizin birden çok maker slotu →
  slot discriminator gerekir; **canlı get_trades şemasına bağlı** (live-blocker).
- **Yazım deseni (ileride):** `confirm_fill_atomic`'in BEGIN IMMEDIATE transaction'ına dahil (atomik,
  position'la diverge etmez); `INSERT OR IGNORE` differing payload'ı MASKELEMEMELİ (conflict→RECOVERY
  pure resolver'da fail-closed).
- **Şimdi schema migration YAPILMAYACAK.** Tetikleyici: incremental-settlement gerçek ihtiyaç VEYA live
  schema doğrulanınca.

## 5. Sıradaki gerçek blocker

**read-only `get_trades` / `get_order` canlı şema doğrulaması.** Pure resolver tüm kararları
fixture-contract v0 üzerinde verir; canlı örnekle doğrulanması gereken açık alanlar:
- `trade_id` benzersizliği/tipi; `status` enum (`TRADE_STATUS_*` gerçek değerleri),
- `taker_order_id` vs `maker_orders[].order_id` semantiği; `matched_amount`/`size`/`price`/`fee_rate_bps`
  alan adları + birimleri,
- `next_cursor` / pagination davranışı (`LTE=` varsayımı),
- maker multi-slot discriminator; asset_id↔token_id; match_time birimi.

Bu doğrulanmadan resolve driver, B2 ledger, fee amount ve canlı reconcile YAZILAMAZ (anayasa madde 3).

## 6. Quant Readiness'a geçmeden açık kapılar

- **Live schema sample** (get_trades/get_order) — AÇIK, ana kapı.
- **Resolve driver** `decide_araf_resolution` → `confirm_fill_atomic` (key=order_intent_id) — AÇIK (yok).
- **Fee amount formula** — rate var, amount yok (base = notional/shares/USDC? rounding?) — canlı-gated AÇIK.
- **Pagination / rate-limit / timeout / backoff client** — AÇIK.
- **B2 settlement ledger** — BACKLOG (blocker değil).
- **Operasyonel:** `NEW_ENTRIES_ENABLED=False`; restart sonrası canlı `logs/mispricing.db`'de
  `execution_state` tablosu doğrulanmalı; DRY_RUN=False config LIVE ama canlı entry yalnız insan yazılı
  komutuyla.

## 7. Paper / read-only live data toplama sırası (önerilen)

1. **read-only get_trades/get_order örnekleme** (NEW_ENTRIES_ENABLED=False altında, yalnız GET; emir yok)
   → v0 fixture varsayımlarını gerçek payload'la doğrula.
2. Fixture-contract v0 → v1 **kalibrasyonu** (alan-adı/enum/birim eşlemesi; mantık aynıysa yalnız map).
3. **Resolve driver (B1)** — karar→write wiring, önce paper.
4. (Opsiyonel) **B2 ledger** — forensic ihtiyaç netleşirse.
5. **Paper P&L / shadow** uçtan uca → sonra canlı (yalnız insanın yazılı komutuyla, DRY_RUN=False).

## Forbidden next actions

- Spec/canlı örnek olmadan `get_trades` şeması uydurma yok.
- Sealed `confirm_fill_atomic`'i tüketici (driver) ve live schema olmadan B2 için değiştirme yok.
- `git add .` / `-A` yok; eski untracked patch'leri (`faz1.patch`, `faz1_code.patch`, `faz1_remaining.patch`,
  `"how --stat 9927708"`) silme/stage etme yok.
- "live-ready / canlıya hazır" iddiası yok.

## NET SONUÇ

**ARAF pure reconcile fazı SEALED.** Pure karar katmanının tüm hedeflenen invariant'ları inşa edildi
(33/33 yeşil, HEAD==origin/master==`f101eac`, anayasa korundu); DB double-run idempotency Task H'de
bağımsız sealed. Kalan her şey canlı get_trades şema doğrulamasına gated = pure resolver kapsamı dışında.
Bir sonraki iş: **read-only canlı şema örnekleme.**
