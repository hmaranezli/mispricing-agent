# Faz 2c-3 — execute() Intent-Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `clob_executor.execute()` içine order-intent yaşam döngüsünü bağla; fill-confirm olmadan position açılmasın, timeout/unknown error'da emir "gitmedi" varsayılmasın.

**Architecture:** Order submission (`post_order`) korunan sınırdır. En erken noktada `has_unresolved_intent` guard; network'ten önce `create_intent` → `SUBMITTED_UNKNOWN` commit; submit sonrası `classify_fill` → `transition`; yalnız FILLED/PARTIAL_FILLED'de position. Position muhasebesi yalnız gerçek API response alanlarından (Decimal). 2a/2b modülleri (`order_intent.py`, `order_pricing.py`, `emergency_pause.py`) DONDU — dokunulmaz.

**Tech Stack:** Python asyncio, aiosqlite, pytest + pytest-asyncio, unittest.mock (patch/AsyncMock/MagicMock), Decimal.

**Operasyon durumu (kodlama anında değişmemeli):** `DRY_RUN=False`, `NEW_ENTRIES_ENABLED=False`, live `dry_run=0` açık pozisyon = 0, emergency_pause aktif değil. main_loop kodlama/test boyunca YENİDEN BAŞLATILMAZ.

---

## Hedef `execute()` akış sırası (clob_executor.py)

```
1. is_emergency_paused()                                  → None     [2c-2 mevcut ✅]
2. token_id resolve + null + position_usd<1 check         → None     [mevcut]
3. has_unresolved_intent(token_id)                        → None     YENİ  ← EN ERKEN; get_quote'tan ÖNCE
4. get_quote (READ) → compute_limit_price pre-validation  → reject → None   [2b mevcut; intent YOK]
   ── buraya kadar create_intent YOK: reddedilen/bloklanan order DB'yi kirletmez ──
5. iid = create_intent(...)              → INTENT_CREATED  commit    YENİ
6. transition(iid, "SUBMITTED_UNKNOWN", submitted_at=ts)  commit     YENİ  ← COMMIT BURADA biter
   ── 5 veya 6 raise (DB fail) → HARD ABORT: ERROR/CRITICAL log + post_order'a GİTME → None ──
   ── 6 fail ise state INTENT_CREATED kalır = "never submitted" (2c-4 reconcile blocker) ──
7. try: get_client / create_market_order / post_order                YENİ wiring
     ├─ Exception "no orders found to match" → transition CANCELLED (FAK_ZERO_FILL)
     │                                          + _handle_fak_no_match telemetri → None
     └─ diğer TÜM Exception (timeout/connection/unknown):
            SUBMITTED_UNKNOWN'da BIRAK, raw error logla, 2. submit YOK → None   [→ 2c-4]
8. (state, exe, reason) = classify_fill(status, taking, requested_est, order_id)   YENİ
9. transition(iid, state, server_order_id=order_id, size_matched=exe, reason)      YENİ
10. is_position_open(state)?  FILLED/PARTIAL → position dict (muhasebe API'den, Decimal; order_intent_id zorunlu)
    ACCEPTED / CANCELLED     → None   [→ 2c-4 reconcile]
```

### Kritik kurallar (red-pen revizyonları)
- **R1 (en erken stop):** `has_unresolved_intent` adım 3'te, `get_quote`'tan ÖNCE. Unresolved varsa pre-validation tarafına bile girilmez.
- **R2 (muhasebe approximate DEĞİL):** `requested_est = position_usd / worst_price` YALNIZCA `classify_fill` içindeki FILLED↔PARTIAL ayrımı için. `shares` ve `size_matched` ve `position_usd` (gerçekleşen) **mutlaka** API response `takingAmount`/`makingAmount`'tan `Decimal` ile türetilir. `requested_est` muhasebeye asla yazılmaz.
- **R3 (lineage):** `positions.order_intent_id` kolonu BU fazda eklenir (idempotent migration). Return dict'te `order_intent_id` zorunlu. (Kolon migration beklenmedik şekilde büyürse fallback: return dict zorunlu + `positions.order_intent_id` 2c-4 öncesi LIVE-BLOCKER olarak kaydedilir — ama tercih: şimdi ekle.)
- **R4 (commit modeli):** Çift commit INTENT_CREATED→SUBMITTED_UNKNOWN; 2a `create_intent`/`transition` imzaları bozulmaz. transition fail → post_order yok, state INTENT_CREATED ("never submitted") → 2c-4 blocker.
- **R5 (DB-fail gözlemlenebilirliği):** create_intent/transition fail veya DB unreadable → hard abort + post_order yok + **ERROR/CRITICAL log kanıtı testte** doğrulanır.
- **R6 (unknown error):** "no orders found to match" DIŞINDAKİ tüm unknown/connection/timeout → SUBMITTED_UNKNOWN'da kal, raw error logla, ikinci submit yok.

---

## File Structure

- **Modify:** `execution/clob_executor.py` — yalnız `execute()` (gerekirse küçük intent-lifecycle helper).
- **Modify:** `db/schema.py` — `_MIGRATIONS` listesine `order_intent_id` ALTER (idempotent).
- **Modify:** `db/logger.py` — `log_position_open` INSERT'ine `order_intent_id` alanı.
- **Create:** `tests/test_execute_intent_wiring.py` — 2c-3 izole test dosyası.
- **Dokunma:** `execution/order_intent.py`, `execution/order_pricing.py`, `execution/emergency_pause.py` (2a/2b dondu).

**Test izolasyonu deseni:** `is_emergency_paused`→AsyncMock False; `get_client`/`get_quote`/`get_shadow_quote` + air_pocket logger patch; `execution.order_intent.DB_FILE` tmp DB'ye patch + `db.schema.init_schema`. Hiçbir testte gerçek network YOK. `caplog` (pytest) ile log kanıtı. Not: `log_position_open` `dry_run`'ı `config.DRY_RUN`'dan türetir; wiring testleri `execute()`'in döndürdüğü dict'i doğrular (DB persist ayrı katman).

---

## Task 0: Schema + lineage kolonu (R3)

**Files:**
- Modify: `db/schema.py` (_MIGRATIONS listesi, ~L467 öncesi)
- Modify: `db/logger.py:116-147` (log_position_open INSERT)
- Test: `tests/test_execute_intent_wiring.py`

- [ ] **Step 1: Failing test** — `test_positions_has_order_intent_id_column`: tmp DB'ye `init_schema`, `PRAGMA table_info(positions)` → `order_intent_id` kolonu var.
- [ ] **Step 2: Run/fail** — `pytest tests/test_execute_intent_wiring.py::test_positions_has_order_intent_id_column -v` → FAIL (kolon yok).
- [ ] **Step 3: Implement** — `_MIGRATIONS` listesine `"ALTER TABLE positions ADD COLUMN order_intent_id TEXT"` ekle. `log_position_open` INSERT kolon+değer listesine `order_intent_id` + `position.get("order_intent_id")` ekle.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit** — `feat(P0 Faz2c-3): positions.order_intent_id lineage kolonu`.

---

## Task A: Unresolved-intent guard EN ERKEN durur (R1)

- [ ] **Step 1: Failing test** — `test_unresolved_intent_blocks_before_quote`: token için DB'ye `create_intent`+`transition(SUBMITTED_UNKNOWN)` seed; `get_quote`=AsyncMock, `get_client`=MagicMock; `execute()` çağır.
  - **Assert:** dönüş `None`; **`get_quote.assert_not_called()`**; `client.post_order.assert_not_called()`.
- [ ] **Step 2: Run/fail** (guard yok → get_quote çağrılır).
- [ ] **Step 3: Implement** — adım 3'te (token_id resolve sonrası, get_quote ÖNCESİ) `if await has_unresolved_intent(None, token_id): log + return None`.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit** — `feat(P0 Faz2c-3): has_unresolved_intent guard (get_quote öncesi)`.

---

## Task B: SUBMITTED_UNKNOWN commit'i network'ten ÖNCE (commit-sınırı kanıtı)

- [ ] **Step 1: Failing test** — `test_submitted_unknown_committed_before_network`:
  - `get_client` öyle patch'lenir ki `create_market_order` (veya `post_order`) side_effect → **ayrı `aiosqlite` connection** ile tmp DB'den `SELECT status,submitted_at FROM order_intents` okur, bir kapanışa kaydeder, sonra fake matched resp döner.
  - **Assert:** readback gerçekten çalıştı (flag True) **ve** okunan `status == "SUBMITTED_UNKNOWN"` **ve** `submitted_at` dolu. Bu, commit'in API çağrısından önce bittiğini kanıtlar.
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — adım 5-6: `iid = await create_intent(None, token_id, "BUY", worst_price, position_usd, slug=...)`; `await transition(None, iid, "SUBMITTED_UNKNOWN", submitted_at=order_submit_ts)`; ANCAK BUNDAN SONRA `post_order`.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit** — `feat(P0 Faz2c-3): create_intent + SUBMITTED_UNKNOWN commit (network öncesi)`.

---

## Task C: create_intent DB fail → hard abort + log kanıtı (R5)

- [ ] **Step 1: Failing test** — `test_create_intent_db_fail_hard_aborts`: `create_intent` patch→`raise sqlite3.OperationalError`; `caplog.at_level(ERROR)`.
  - **Assert:** dönüş `None`; `client.post_order.assert_not_called()`; caplog'da ERROR/CRITICAL kayıt (hard abort).
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — adım 5'i try/except'e al; except → `logger.critical(...)` + `return None` (post_order'a gitme).
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit.**

---

## Task D: transition(SUBMITTED_UNKNOWN) DB fail → hard abort, state INTENT_CREATED (R4/R5)

- [ ] **Step 1: Failing test** — `test_transition_presubmit_fail_hard_aborts_stays_intent_created`: `create_intent` gerçek (INTENT_CREATED yazılır); pre-submit `transition` patch→raise; `caplog`.
  - **Assert:** dönüş `None`; `post_order.assert_not_called()`; DB'de intent `status=="INTENT_CREATED"` ("never submitted"); ERROR/CRITICAL log var.
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — adım 6'yı try/except'e al; except → critical log + return None.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit** — not: 2c-4 reconcile planına "INTENT_CREATED = never submitted" blocker maddesi.

---

## Task E: Timeout → SUBMITTED_UNKNOWN'da kalır, tek submit, raw log (R6)

- [ ] **Step 1: Failing test** — `test_timeout_leaves_submitted_unknown_no_resubmit`: `post_order` side_effect→`TimeoutError("..")`; `caplog`.
  - **Assert:** dönüş `None`; DB intent `status=="SUBMITTED_UNKNOWN"`; `post_order.call_count == 1` (resubmit yok); position yok; caplog'da raw error metni.
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — except bloğunda: "no orders found to match" değilse → raw error log + `return None` (transition ÇAĞRILMAZ; state zaten SUBMITTED_UNKNOWN).
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit.**

---

## Task F: ConnectionError / generic unknown → SUBMITTED_UNKNOWN (R6)

- [ ] **Step 1: Failing test** — `test_connection_error_stays_unknown`: `post_order`→`ConnectionError`; ayrıca generic `Exception("503 upstream")` için parametrize.
  - **Assert:** intent `SUBMITTED_UNKNOWN`; position yok; raw error log; resubmit yok.
- [ ] **Step 2-4:** Task E implementasyonu kapsar (ek kod gerekmeyebilir; test doğrular).
- [ ] **Step 5: Commit** (Task E ile birleşebilir).

---

## Task G: "no orders found to match" → CANCELLED + telemetri, position yok

- [ ] **Step 1: Failing test** — `test_no_orders_found_transitions_cancelled`: `post_order`→`Exception("... no orders found to match ...")`; `get_shadow_quote` + `log_entry_air_pocket` patch.
  - **Assert:** dönüş `None`; DB intent `status=="CANCELLED"`, `reconciliation_reason` FAK_ZERO_FILL içerir; `_handle_fak_no_match` (air_pocket telemetri) çağrıldı; position yok.
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — except içinde "no orders found to match" branch: `await transition(None, iid, "CANCELLED", reason="FAK_ZERO_FILL")` → sonra mevcut `_handle_fak_no_match(...)` → `return None`.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit.**

---

## Task H: Matched FULL fill → position FILLED, muhasebe API'den Decimal (R2)

- [ ] **Step 1: Failing test** — `test_matched_full_fill_opens_position_filled`: fake resp `status="matched", takingAmount="71.43", makingAmount="25.00", orderID="ord-1"`.
  - **Assert:** position dict döner; `order_intent_id == iid` (dolu); DB intent `status=="FILLED"`, `size_matched==71.43`; `position["shares"] == Decimal/float(taking)`, `position["position_usd"] == float(making)` (gerçek API'den, `requested_est` DEĞİL); `position["pm_entry_price"] == making/taking` (Decimal türetme).
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3: Implement** — adım 8-10: `requested_est = float(Decimal(str(position_usd))/Decimal(str(worst_price)))` yalnız classify için; `classify_fill(status, taking_amount, requested_est, order_id)`; `transition(..., size_matched=exe)`; muhasebe `shares=float(taking)`, `pos_usd=float(making)`, `fill_price=round(making/taking,6)` (mevcut mantık, Decimal ara hesap); position dict'e `"order_intent_id": iid` ekle.
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit** — `feat(P0 Faz2c-3): classify_fill→transition→position (FILLED, gerçek API muhasebesi)`.

---

## Task I: Matched PARTIAL fill → position PARTIAL_FILLED (yine açılır)

- [x] **Step 1: Failing test** — `test_matched_partial_fill_opens_position`: `takingAmount` < requested_est (örn taking=10, making=4, position_usd=25).
  - **Assert:** DB intent `status=="PARTIAL_FILLED"`; position dict **yine döner** (open state); `shares==10`, `position_usd==4` (API'den, approximate değil).
- [x] **Step 2-4:** Task H kapsar; test doğrular.
- [x] **Step 5: Commit** (H ile birleşti).

> **CLOSURE (2026-06-11) — DONE / Task H ile tam subsumed.**
> Kanıt: `tests/test_execute_intent_wiring.py:837` `test_partial_fill_persists_partial_filled_with_aggregate_slippage` PASS → intent `PARTIAL_FILLED`, pozisyon açılıyor, muhasebe API'den. Spec semantiği uygulandı. Ek iş yok.

---

## Task J: ACCEPTED / no_fill_proof → position YOK (2c-4'e kalır)

- [ ] **Step 1: Failing test** — `test_accepted_no_fill_proof_no_position`: resp `status="live", orderID="srv-1"`, takingAmount yok → mevcut `matched` kontrolü zaten None döndürebilir; ama intent state doğrulanmalı.
  - **Assert:** dönüş `None`; DB intent `status=="ACCEPTED"`, `reconciliation_reason=="no_fill_proof"`; position yok.
- [ ] **Step 2: Run/fail** (bugün transition çağrılmıyor → intent SUBMITTED_UNKNOWN kalır, ACCEPTED değil).
- [ ] **Step 3: Implement** — adım 9 her durumda transition çağırır; `is_position_open(state)` False → return None. (classify "live"+order_id → ACCEPTED.)
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit.**

> **CLOSURE (2026-06-11) — KISMİ. Güvenlik kapalı, status semantiği Faz 2c-4'e DEFERRED.**
> - **Kapalı (güvenlik invariantı):** `tests/test_execute_intent_wiring.py:1046` `test_no_fill_proof_blocks_submitted_unknown_no_position` PASS → no-fill-proof'ta **sahte pozisyon açılmıyor** (`confirm_fill_atomic` asla çağrılmaz, `positions` count 0).
> - **Uygulanmamış (spec semantiği):** intent `ACCEPTED` + `reconciliation_reason=="no_fill_proof"` transition'ı YOK; gerçek davranış intent'i **`SUBMITTED_UNKNOWN`** bırakıyor. Bu kasıtlı — planın kendi başlığı "(2c-4'e kalır)".
> - **Sonraki:** ACCEPTED status transition'ı Faz 2c-4 reconcile / recovery-ladder resolve protokolünde ele alınacak. "DONE" sayılmaz.

---

## Task K: Matched taking=0 → CANCELLED, position yok

- [ ] **Step 1: Failing test** — `test_zero_fill_matched_cancelled_no_position`: resp `status="matched", takingAmount="0"`.
  - **Assert:** intent `status=="CANCELLED"` reason FAK_ZERO_FILL; dönüş `None`; position yok.
- [ ] **Step 2: Run/fail.**
- [ ] **Step 3:** Task H/J implementasyonu kapsar (classify→CANCELLED→is_position_open False).
- [ ] **Step 4: Run/pass.**
- [ ] **Step 5: Commit.**

> **CLOSURE (2026-06-11) — KISMİ. Güvenlik kapalı, CANCELLED semantiği Faz 2c-4'e DEFERRED.**
> - **Kapalı (güvenlik invariantı):** matched+taking=0'da pozisyon açılmıyor — `tests/test_execute_intent_wiring.py:1046` (H4-10) aynı senaryoyu kapsıyor (`positions` count 0).
> - **Spec'ten FARK:** matched+taking=0 şu an `CANCELLED`+`FAK_ZERO_FILL` DEĞİL, **`SUBMITTED_UNKNOWN`** (no_fill_proof) olarak ele alınıyor. `CANCELLED`+`FAK_ZERO_FILL` semantiği yalnız Task G "no orders found to match" exception path'inde mevcut (`tests/test_execute_intent_wiring.py:595-702` PASS) — bu farklı bir senaryo.
> - **Sonraki:** "matched ama taking=0" intent'inin doğru terminal status'u (CANCELLED mi, recovery mi) Faz 2c-4 reconcile protokolünde kararlaştırılacak. "DONE" sayılmaz.

---

## Self-Review / Spec coverage

| Handoff invariant | Görev |
|---|---|
| emergency_paused gate (2c-2) | mevcut ✅ (regression korur) |
| has_unresolved_intent EN ERKEN (R1) | A |
| DB fail/create_intent/transition fail → hard abort, submit yok + log (R5) | C, D |
| network öncesi intent + SUBMITTED_UNKNOWN commit, readback kanıtı | B |
| timeout/unknown → SUBMITTED_UNKNOWN, raw log, resubmit yok (R6) | E, F |
| no orders found → CANCELLED + telemetri | G |
| classify_fill→transition→position yalnız FILLED/PARTIAL; muhasebe API+Decimal (R2) | H, I |
| ACCEPTED/no_fill_proof → position yok, 2c-4 | J |
| zero-fill CANCELLED | K |
| lineage order_intent_id (R3) | 0, H |
| monotonic guard korunur (2b) | 2b regression + H/J ileri-yol |
| commit modeli çift, 2a bozulmaz (R4) | B, D |
| dry_run=False position dict | H |

**2c-4 reconcile planına devredilen blocker maddeleri:** (a) `INTENT_CREATED` = "never submitted" sayılmalı; (b) `SUBMITTED_UNKNOWN` = get_trades heuristic eşleme; (c) `ACCEPTED/no_fill_proof` = fill kanıtı arama; (d) lineage join `positions.order_intent_id ↔ order_intents`.

---

## Operasyon Güvenliği Planı (kodlamadan ÖNCE — AYRI onay gerekir)

### Kodlamadan önce read-only kanıtlar
1. `pgrep -fa "main_loop|watch_20trades|pytest"` + `ps` snapshot.
2. `git status --short` (temiz ağaç).
3. Guardrail grep: `DRY_RUN=False`, `NEW_ENTRIES_ENABLED=False`, `MIN_EDGE_PCT=0.05`.
4. `SELECT COUNT(*) FROM positions WHERE status='open' AND dry_run=0` → 0.
5. `SELECT emergency_paused,reason,source FROM execution_state` (paused değil).
6. Durdurma SONRASI: aynı `pgrep` boş (hedefli pytest hariç).

### Güvenli durdurma (AYRI onayla)
1. **Graceful önce:** `kill -TERM <main_loop_pid>` → grace bekle → `pgrep` ile gittiğini doğrula (live + DRY_RUN=False → graceful zorunlu).
2. Eski `watch_20trades.py` + takılı pytest blast koşuları: doğal bitmezse SIGTERM.
3. **`kill -9` yalnız son çare** (SIGTERM'e grace sonunda yanıt yoksa).
4. Eski bash sarmalayıcıları zararsız; gerekirse temizlik.

### Kodlama/test boyunca
- **main_loop YENİDEN BAŞLATILMAZ.** Yalnız `pytest tests/test_execute_intent_wiring.py` + blast-radius seti; canlı loop asla başlatılmaz.
- Testler tmp DB → canlı `logs/mispricing.db`'ye dokunmaz.
- Bitince (AYRI onay): full regression + blast yeşil → `graphify update .` → commit/push → **restart kararı insana ait**.
