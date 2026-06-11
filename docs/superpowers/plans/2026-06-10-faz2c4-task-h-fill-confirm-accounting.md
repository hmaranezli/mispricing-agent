# Faz 2c — Task H: Fill-Confirm Atomic Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `clob_executor.execute()` başarılı `post_order` response'unu tek-transaction atomik muhasebeye bağla: yalnız gerçek+yeterli fill/cost kanıtı varsa position aç (FILLED/PARTIAL_FILLED), aksi halde bloklayıcı/recovery state; "terminal intent var ama position yok" ve "zombi position" ASLA oluşmasın; duplicate accounting DB+app çift kilidiyle engellensin.

**Architecture:** `post_order` korunan sınır (2c-3 ✅). Başarılı response → `classify_fak_fill` (USD-denominated, Decimal, saf fonksiyon) → karar. Position açılacaksa `confirm_fill_atomic` TEK aiosqlite connection + `BEGIN IMMEDIATE` içinde position INSERT + order_intents UPDATE→terminal yapar; herhangi biri fail → tüm transaction rollback. Cost yoksa / FAK invariant breach → `RECOVERY_REQUIRED` + CRITICAL, position yok. DB accounting tek kaynağa (`execute()`) taşınır; `main_loop` telemetri/notify görünürlüğünü korur ama ikinci kez DB'ye yazmaz.

**Tech Stack:** Python asyncio, aiosqlite, sqlite3 (sync readback testlerinde), pytest + pytest-asyncio, unittest.mock (patch/AsyncMock/MagicMock), Decimal.

**Operasyon durumu (kodlama anında değişmemeli):** `DRY_RUN=False`, `NEW_ENTRIES_ENABLED=False`, live `dry_run=0` açık pozisyon = 0, emergency_pause aktif değil. main_loop kodlama/test boyunca YENİDEN BAŞLATILMAZ. Network yok; tüm testler tmp DB. push yalnız insan onayıyla.

**Onaylı muhasebe anayasası (insan kararı, bağlayıcı):** Gerçek ve yeterli fill/cost kanıtı yoksa position yok.

---

## Onaylı kararlar (red-pen → kilitli)

| # | Karar |
|---|-------|
| D1 Denominasyon | FILLED↔PARTIAL ayrımı **USD**: `makingAmount` (gerçek harcanan) vs `position_usd` (istenen). `takingAmount` = shares; USD `requested` ile kıyaslanmaz. `shares` yalnız `takingAmount`'tan. Tüm fill aritmetiği `Decimal`. |
| D2 No-fill-proof | Canlı FAK path'inde `ACCEPTED` KULLANILMAZ. `order_id`/accepted ama matched/executed kanıtı yok → intent `SUBMITTED_UNKNOWN` (bloklayıcı, `has_unresolved_intent`). status `live/delayed/open/resting` (FAK invariant breach) → `RECOVERY_REQUIRED` + CRITICAL. |
| D3 Cost yok → position yok | `takingAmount`>0 ama `makingAmount`/cost yok → position AÇMA. `position_usd`/limit price ile cost UYDURMA → `RECOVERY_REQUIRED` + CRITICAL/ERROR → 2c-4. |
| D4 Schema | `positions(order_intent_id)` partial UNIQUE index `WHERE order_intent_id IS NOT NULL`. `positions.shares REAL` nullable. Migration backfill-safe (eski satır bozulmaz), idempotent, testli. |
| D5 Atomicity | Atomik confirm `execute()`/helper'da TEK connection, TEK transaction, TEK COMMIT. INSERT başarılı + intent terminal UPDATE fail → rollback (zombi position yasak). intent FILLED/PARTIAL ama position yok yasak. main_loop ikinci DB accounting yazmaz; telemetri/log korunur. |
| D6 Partial / duplicate | Partial sonrası remaining = dead (FAK); cancel emri YOK. response open/resting/live/delayed → invariant breach → RECOVERY. Aynı `order_intent_id` ikinci Task H/2c-4 → ikinci position YOK (DB UNIQUE + app precheck). Tekrar fill/response işleme denemesi de testlenir. |

---

## Hedef `execute()` akışı — adım 8-10 (2c-3'te boş bırakılan başarılı path)

```
... (2c-3 ✅: emergency_pause → guard → quote/prevalidation → create_intent → SUBMITTED_UNKNOWN → post_order)
post_order BAŞARILI (resp döndü, exception yok):
  8.  decision = classify_fak_fill(status, takingAmount, makingAmount, requested_usd=position_usd, order_id)
  9.  decision.kind:
       ├─ OPEN_FILLED   → confirm_fill_atomic(iid, position_row, terminal="FILLED")
       ├─ OPEN_PARTIAL  → confirm_fill_atomic(iid, position_row, terminal="PARTIAL_FILLED")
       ├─ BLOCK_UNKNOWN → (no-fill-proof + order_id) intent SUBMITTED_UNKNOWN'da BIRAK → None   [→2c-4]
       ├─ TERMINAL_ZERO → transition CANCELLED (FAK_ZERO_FILL) → None                            [terminal]
       └─ RECOVERY      → recovery_ladder(iid, reason) → None  (cost-missing / invariant-breach)
  10. confirm_fill_atomic sonucu:
       ├─ OK            → persisted position dict (order_intent_id + shares dahil) RETURN
       └─ FAIL (DB)     → recovery_ladder(iid, "CONFIRM_TX_FAILED") → None
```

`recovery_ladder(iid, reason)`:
```
1. transition(iid, "RECOVERY_REQUIRED", reason=reason, size/order_id capture)  + CRITICAL log
   fail ↓
2. set_emergency_pause(reason="task_h_recovery_write_failed", order_intent_id=iid) + CRITICAL
   fail ↓
3. CRITICAL log (son çare): sonraki execute() is_emergency_paused fail-closed=True ile zaten bloklu
```

---

## Değişecek / oluşacak dosyalar

| Dosya | Sorumluluk | Değişiklik |
|-------|-----------|------------|
| `db/schema.py` | şema + migration | `shares` kolonu + partial UNIQUE index (`_MIGRATIONS`'a) |
| `execution/order_intent.py` | state machine + fill sınıflama | `classify_fak_fill` (yeni saf fn) + `confirm_fill_atomic` (yeni, tek-txn) |
| `execution/clob_executor.py` | execute() wiring | adım 8-10 + `recovery_ladder`; başarılı response → classify → confirm/recovery |
| `main_loop.py` | tarama/telemetri | `_scan_and_execute`: execute() artık persist ettiği için 2. `log_position_open` DB accounting kaldır; notify/telemetri korunur |
| `tests/test_task_h_fill_confirm.py` | yeni test dosyası | classify_fak_fill + confirm_fill_atomic + execute wiring + recovery + duplicate |
| `tests/test_execute_intent_wiring.py` | mevcut | Task H execute-path testleri (E/F/G yanına) |
| `tests/test_db_schema_migration.py` | yeni/var | shares + UNIQUE index migration backfill-safe testleri |

**DONMUŞ (dokunulmaz):** `config.py`, `execution/order_pricing.py`, `execution/emergency_pause.py` (yalnız çağrılır), 2c-3'te yazılan Task A/B/C-D/E/F/G mantığı.

**Not (classify_fill vs classify_fak_fill):** Mevcut `order_intent.classify_fill` (`test_fill_confirm.py` kullanıyor) DOKUNULMAZ; regresyon riski için yeni `classify_fak_fill` eklenir (USD-denominated + makingAmount + breach ayrımı). `classify_fill` 2c-4'te deprecate değerlendirilir.

---

### Task H0: Schema — `shares` kolonu + partial UNIQUE index (backfill-safe)

**Files:**
- Modify: `db/schema.py` (`_MIGRATIONS` listesi)
- Test: `tests/test_db_schema_migration.py`

- [ ] **Step 1: Failing test — yeni kolon + index + legacy korunur**

```python
import sqlite3, tempfile, aiosqlite, pytest
from pathlib import Path
from db.schema import init_schema

async def _fresh(path):
    conn = await aiosqlite.connect(str(path)); await init_schema(conn); await conn.close()

@pytest.mark.asyncio
async def test_positions_has_shares_column_and_unique_index():
    d = Path(tempfile.mkdtemp()) / "t.db"
    await _fresh(d)
    conn = await aiosqlite.connect(str(d))
    cols = [r[1] for r in await (await conn.execute("PRAGMA table_info(positions)")).fetchall()]
    idx  = [r[1] for r in await (await conn.execute("PRAGMA index_list(positions)")).fetchall()]
    await conn.close()
    assert "shares" in cols, f"shares kolonu eklenmeli: {cols}"
    assert any("order_intent_id" in i for i in idx), f"order_intent_id UNIQUE index olmalı: {idx}"

@pytest.mark.asyncio
async def test_partial_unique_index_blocks_duplicate_intent_but_allows_null():
    d = Path(tempfile.mkdtemp()) / "t.db"
    await _fresh(d)
    conn = await aiosqlite.connect(str(d))
    base = ("ts_open","slug","asset","action","status","dry_run")
    async def ins(pid, oiid):
        await conn.execute(
            "INSERT INTO positions (position_id, ts_open, slug, asset, action, status, dry_run, order_intent_id)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (pid,"2026-06-10T00:00:00","s","BTC","YES","open",0,oiid)); await conn.commit()
    await ins("p1","intent-1")
    await ins("p2", None)          # NULL serbest (eski/dry pozisyonlar)
    await ins("p3", None)          # ikinci NULL da serbest (partial index)
    with pytest.raises(sqlite3.IntegrityError):
        await ins("p4","intent-1") # AYNI intent-id ikinci kez → UNIQUE breach
    await conn.close()

@pytest.mark.asyncio
async def test_migration_idempotent_and_preserves_legacy_rows():
    d = Path(tempfile.mkdtemp()) / "legacy.db"
    conn = await aiosqlite.connect(str(d))
    await conn.execute("CREATE TABLE positions (position_id TEXT PRIMARY KEY, slug TEXT)")
    await conn.execute("INSERT INTO positions (position_id, slug) VALUES ('old','s')")
    await conn.commit()
    await init_schema(conn)          # migration uygula
    await init_schema(conn)          # idempotent re-run (restart sim)
    row = await (await conn.execute(
        "SELECT position_id, slug, shares, order_intent_id FROM positions WHERE position_id='old'")).fetchone()
    await conn.close()
    assert row == ("old","s",None,None), f"legacy satır korunmalı, yeni kolonlar NULL: {row}"
```

- [ ] **Step 2: Run → FAIL** — `pytest tests/test_db_schema_migration.py -v` → "no such column: shares" / index yok.

- [ ] **Step 3: Minimal migration** — `db/schema.py` `_MIGRATIONS` listesine ekle (mevcut try/except OperationalError ile idempotent):

```python
"ALTER TABLE positions ADD COLUMN shares REAL",
"CREATE UNIQUE INDEX IF NOT EXISTS ix_positions_order_intent_id "
"ON positions(order_intent_id) WHERE order_intent_id IS NOT NULL",
```
Not: ALTER iki kez → `OperationalError` yutulur (mevcut migration döngüsü). Partial UNIQUE index sqlite 3.8+ desteklenir.

- [ ] **Step 4: Run → PASS** — 3 test yeşil; mevcut `test_execute_intent_wiring.py` schema testleri bozulmaz.

- [ ] **Step 5: Commit** — `test(P0 Faz2c Task H0): positions.shares + partial UNIQUE(order_intent_id) migration`

---

### Task H1: `classify_fak_fill` — USD-denominated, Decimal, breach-aware saf fonksiyon

**Files:**
- Modify: `execution/order_intent.py`
- Test: `tests/test_task_h_fill_confirm.py`

Karar nesnesi (yeni, saf): `classify_fak_fill(status, taking_amount, making_amount, requested_usd, order_id) -> dict`
Dönüş alanları: `kind` ∈ {`OPEN_FILLED`,`OPEN_PARTIAL`,`BLOCK_UNKNOWN`,`TERMINAL_ZERO`,`RECOVERY`}, `state`, `shares` (Decimal|None), `spent_usd` (Decimal|None), `fill_price` (Decimal|None), `reason`.

- [ ] **Step 1: Failing test — tüm dallar**

```python
from decimal import Decimal
from execution.order_intent import classify_fak_fill as C

def test_full_fill_usd_denominated():
    d = C(status="matched", taking_amount="71.43", making_amount="25.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_FILLED" and d["state"] == "FILLED"
    assert d["shares"] == Decimal("71.43") and d["spent_usd"] == Decimal("25.00")
    assert d["fill_price"] == (Decimal("25.00")/Decimal("71.43")).quantize(Decimal("0.000001"))

def test_partial_fill_usd_denominated():
    d = C(status="matched", taking_amount="40.00", making_amount="14.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED"
    assert d["shares"] == Decimal("40.00") and d["spent_usd"] == Decimal("14.00")

def test_zero_fill_no_order_id_is_terminal_cancelled():
    d = C(status="unmatched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id=None)
    assert d["kind"] == "TERMINAL_ZERO" and d["state"] == "CANCELLED" and d["reason"] == "FAK_ZERO_FILL"

def test_zero_fill_with_order_id_blocks_submitted_unknown():
    d = C(status="matched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id="ord-x")     # order_id var ama fill kanıtı yok
    assert d["kind"] == "BLOCK_UNKNOWN" and d["state"] == "SUBMITTED_UNKNOWN"

def test_resting_status_is_invariant_breach_recovery():
    for st in ("live", "delayed", "open"):
        d = C(status=st, taking_amount="0", making_amount="0",
              requested_usd="25.00", order_id="ord-x")
        assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
        assert "INVARIANT_BREACH" in d["reason"]

def test_shares_present_but_cost_missing_is_recovery():
    d = C(status="matched", taking_amount="40.00", making_amount=None,
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
    assert d["reason"] == "FILL_COST_MISSING" and d["shares"] == Decimal("40.00")
    assert d["spent_usd"] is None     # cost UYDURULMAZ
```

- [ ] **Step 2: Run → FAIL** — `classify_fak_fill` import edilemez / tanımsız.

- [ ] **Step 3: Minimal implementation** (`execution/order_intent.py`):

```python
from decimal import Decimal

_RESTING = ("live", "delayed", "open", "resting")

def classify_fak_fill(status, taking_amount, making_amount, requested_usd, order_id=None):
    """FAK BUY response → karar. USD-denominated (D1). Cost yoksa position yok (D3).
    Resting/open = FAK invariant breach (D2/D6). Saf fonksiyon, DB'ye dokunmaz."""
    s = (status or "").lower()
    taking = Decimal(str(taking_amount or 0))
    making = None if making_amount is None else Decimal(str(making_amount))
    req    = Decimal(str(requested_usd))

    # FAK invariant breach: emir dinleniyor/açık → RECOVERY (D2/D6)
    if s in _RESTING:
        return dict(kind="RECOVERY", state="RECOVERY_REQUIRED", shares=None,
                    spent_usd=None, fill_price=None, reason="FAK_INVARIANT_BREACH_RESTING")

    # Fill kanıtı (shares) yok
    if taking <= 0:
        if order_id:   # borsa order_id verdi ama fill kanıtı yok → araf (bloklayıcı)
            return dict(kind="BLOCK_UNKNOWN", state="SUBMITTED_UNKNOWN", shares=None,
                        spent_usd=None, fill_price=None, reason="no_fill_proof")
        return dict(kind="TERMINAL_ZERO", state="CANCELLED", shares=Decimal("0"),
                    spent_usd=Decimal("0"), fill_price=None, reason="FAK_ZERO_FILL")

    # shares var ama cost yok → position UYDURULMAZ (D3)
    if making is None or making <= 0:
        return dict(kind="RECOVERY", state="RECOVERY_REQUIRED", shares=taking,
                    spent_usd=None, fill_price=None, reason="FILL_COST_MISSING")

    fill_price = (making / taking).quantize(Decimal("0.000001"))
    # USD-denominated tamlık (D1): harcanan ≥ istenen*0.999 → FILLED, değilse PARTIAL
    if making >= req * Decimal("0.999"):
        return dict(kind="OPEN_FILLED", state="FILLED", shares=taking,
                    spent_usd=making, fill_price=fill_price, reason=None)
    return dict(kind="OPEN_PARTIAL", state="PARTIAL_FILLED", shares=taking,
                spent_usd=making, fill_price=fill_price, reason=None)
```

- [ ] **Step 4: Run → PASS** — 6 test yeşil; mevcut `classify_fill` testleri (`test_fill_confirm.py`) etkilenmez.

- [ ] **Step 5: Commit** — `feat(P0 Faz2c Task H1): classify_fak_fill USD-denominated Decimal breach-aware`

---

### Task H2: `confirm_fill_atomic` — tek connection, tek transaction (D5)

**Files:**
- Modify: `execution/order_intent.py`
- Test: `tests/test_task_h_fill_confirm.py`

İmza: `async def confirm_fill_atomic(db_path, order_intent_id, position_row: dict, terminal_state: str) -> str`
Dönüş: `"OPENED"` (yazıldı), `"DUPLICATE"` (zaten var, no-op), raise (DB fail → çağıran recovery'e gider).

- [ ] **Step 1: Failing test — atomicity + duplicate + rollback**

```python
import sqlite3, tempfile, aiosqlite, pytest
from pathlib import Path
from db.schema import init_schema
from execution.order_intent import create_intent, transition, confirm_fill_atomic

async def _db():
    d = Path(tempfile.mkdtemp()) / "t.db"
    conn = await aiosqlite.connect(str(d)); await init_schema(conn); await conn.close()
    return str(d)

def _posrow(oiid, pid="pos-1"):
    return {"position_id": pid, "opened_at": "2026-06-10T12:00:00+00:00",
            "slug": "btc-x", "asset": "BTC", "action": "YES", "pm_entry_price": 0.35,
            "fair_value": 0.55, "ref_price": 95000.0, "edge": 0.2, "position_usd": 25.0,
            "kelly_f": 0.15, "confidence_score": 82.0, "shares": 71.43, "dry_run": 0,
            "status": "open", "order_intent_id": oiid}

@pytest.mark.asyncio
async def test_confirm_writes_position_and_terminal_intent_atomically():
    db = await _db()
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    res = await confirm_fill_atomic(db, iid, _posrow(iid), "FILLED")
    assert res == "OPENED"
    c = sqlite3.connect(db)
    prow = c.execute("SELECT order_intent_id, shares FROM positions WHERE order_intent_id=?", (iid,)).fetchone()
    irow = c.execute("SELECT status, size_matched FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()
    c.close()
    assert prow == (iid, 71.43), f"position yazılmalı, lineage+shares: {prow}"
    assert irow[0] == "FILLED", f"intent terminal FILLED: {irow}"

@pytest.mark.asyncio
async def test_duplicate_intent_second_confirm_is_noop_no_second_position():
    db = await _db()
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    await confirm_fill_atomic(db, iid, _posrow(iid, "pos-1"), "FILLED")
    res2 = await confirm_fill_atomic(db, iid, _posrow(iid, "pos-2"), "FILLED")  # tekrar
    assert res2 == "DUPLICATE"
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 1, f"ikinci position AÇILMAMALI: {n}"

@pytest.mark.asyncio
async def test_intent_update_fail_rolls_back_position_no_zombie(monkeypatch):
    """intent UPDATE patlatılır → tüm txn rollback: position YAZILMAMALI, intent terminal DEĞİL."""
    db = await _db()
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    # confirm_fill_atomic içindeki intent UPDATE'i bozacak şekilde geçersiz terminal state ver:
    with pytest.raises(Exception):
        await confirm_fill_atomic(db, iid, _posrow(iid), "NOT_A_STATE")  # whitelist dışı → raise
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    st = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 0, f"intent UPDATE fail → position ROLLBACK olmalı (zombi yok): {n}"
    assert st == "SUBMITTED_UNKNOWN", f"intent terminal OLMAMALI (rollback): {st}"
```

- [ ] **Step 2: Run → FAIL** — `confirm_fill_atomic` tanımsız.

- [ ] **Step 3: Minimal implementation** (`execution/order_intent.py`):

```python
async def confirm_fill_atomic(db_path, order_intent_id, position_row, terminal_state):
    """Position INSERT + intent terminal UPDATE'i TEK connection/TEK transaction'da yapar (D5).
    Herhangi biri fail → BEGIN…ROLLBACK → ne position ne terminal intent (zombi yok).
    Aynı order_intent_id zaten varsa → no-op 'DUPLICATE' (D6 idempotency)."""
    if terminal_state not in ("FILLED", "PARTIAL_FILLED"):
        raise ValueError(f"confirm yalnız FILLED/PARTIAL_FILLED: {terminal_state}")
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        try:
            await conn.execute("BEGIN IMMEDIATE")
            # App-level precheck (DB UNIQUE index ile çift kilit — D6)
            async with conn.execute(
                "SELECT 1 FROM positions WHERE order_intent_id=?", (order_intent_id,)) as cur:
                if await cur.fetchone():
                    await conn.execute("ROLLBACK")
                    return "DUPLICATE"
            await conn.execute(
                """INSERT INTO positions (position_id, ts_open, slug, asset, action,
                       pm_entry_price, fair_value, ref_price, edge, position_usd, kelly_f,
                       confidence_score, shares, status, dry_run, order_intent_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (position_row["position_id"], position_row["opened_at"], position_row["slug"],
                 position_row["asset"], position_row["action"], position_row["pm_entry_price"],
                 position_row["fair_value"], position_row["ref_price"], position_row["edge"],
                 position_row["position_usd"], position_row["kelly_f"],
                 position_row["confidence_score"], position_row["shares"],
                 position_row.get("status", "open"), position_row.get("dry_run", 0),
                 order_intent_id))
            await conn.execute(
                "UPDATE order_intents SET status=?, size_matched=?, exchange_order_id=?, "
                "updated_at=? WHERE order_intent_id=?",
                (terminal_state, position_row["shares"], position_row.get("order_id"),
                 now, order_intent_id))
            await conn.execute("COMMIT")
            return "OPENED"
        except BaseException:
            try:
                await conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
```
Not: precheck whitelist (`terminal_state`) BEGIN'den önce raise eder → bu testte position hiç yazılmaz; INSERT-sonrası UPDATE fail senaryosu Task H3 exception-injection testinde (gerçek DB hatası enjekte) ayrıca kanıtlanır.

- [ ] **Step 4: Run → PASS** — 3 test yeşil.

- [ ] **Step 5: Commit** — `feat(P0 Faz2c Task H2): confirm_fill_atomic single-transaction position+intent (no zombie)`

---

### Task H2b: INSERT-sonrası UPDATE fail → gerçek rollback kanıtı (exception injection)

**Files:**
- Test: `tests/test_task_h_fill_confirm.py`

- [ ] **Step 1: Failing test — UPDATE aşamasında DB hatası enjekte**

```python
@pytest.mark.asyncio
async def test_update_fail_after_insert_rolls_back(monkeypatch):
    """INSERT başarılı olduktan SONRA intent UPDATE DB hatası fırlatırsa tüm txn rollback olmalı:
    position satırı COMMIT edilmemeli (zombi yasak), intent SUBMITTED_UNKNOWN kalmalı."""
    import execution.order_intent as oi
    db = await _db()
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")

    real_execute = aiosqlite.Connection.execute
    async def _boom(self, sql, *a, **k):
        if sql.strip().upper().startswith("UPDATE ORDER_INTENTS"):
            raise sqlite3.OperationalError("database is locked")  # UPDATE anında patlat
        return await real_execute(self, sql, *a, **k)
    monkeypatch.setattr(aiosqlite.Connection, "execute", _boom)

    with pytest.raises(sqlite3.OperationalError):
        await confirm_fill_atomic(db, iid, _posrow(iid), "FILLED")
    monkeypatch.undo()
    c = sqlite3.connect(db)
    n  = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    st = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 0,  f"UPDATE fail → INSERT geri alınmalı (zombi position yok): {n}"
    assert st == "SUBMITTED_UNKNOWN", f"intent terminal OLMAMALI: {st}"
```

- [ ] **Step 2: Run → FAIL veya PASS ölç** — Task H2 implementasyonu `BEGIN IMMEDIATE`/`ROLLBACK` ile doğru ise PASS (atomicity kanıtı, regression lock). FAIL ederse confirm_fill_atomic'te transaction sınırını düzelt (autocommit kapalı, tek COMMIT).

- [ ] **Step 3: (gerekirse) düzelt** — `BEGIN IMMEDIATE` + explicit `COMMIT`/`ROLLBACK`; aiosqlite `isolation_level` davranışını doğrula.

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit** — `test(P0 Faz2c Task H2b): prove INSERT+UPDATE atomic rollback under injected DB fault`

---

### Task H3: `execute()` wiring + recovery ladder (adım 8-10)

**Files:**
- Modify: `execution/clob_executor.py` (post_order başarılı dalı + `recovery_ladder`)
- Test: `tests/test_execute_intent_wiring.py`

- [ ] **Step 1: Failing tests — full / partial / no-fill-proof / cost-missing / breach / confirm-DB-fail**

```python
# Helper'lar mevcut dosyadaki _finding/_gate/_risk/_qask/_fresh_db desenini kullanır.
def _resp(status="matched", taking="71.43", making="25.00", oid="ord"):
    return {"status": status, "success": True, "orderID": oid,
            "takingAmount": taking, "makingAmount": making}

@pytest.mark.asyncio
async def test_full_fill_opens_filled_position_with_lineage_and_shares():
    import execution.order_intent as oi
    finding = _finding("YES"); token_id = finding["yes_token_id"]; db_path = str(oi.DB_FILE)
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(making="25.00", taking="71.43")
    with patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(finding, _gate(), _risk(), [])
    assert pos is not None and pos["status"] == "open"
    assert pos["order_intent_id"] and pos["shares"] == 71.43
    c = sqlite3.connect(db_path)
    irow = c.execute("SELECT status, size_matched FROM order_intents WHERE market_token_id=?", (token_id,)).fetchone()
    prow = c.execute("SELECT order_intent_id, shares, position_usd FROM positions WHERE order_intent_id=?", (pos["order_intent_id"],)).fetchone()
    c.close()
    assert irow[0] == "FILLED"
    assert prow[1] == 71.43 and prow[2] == 25.0     # size GERÇEK fill'den (D1/D6)

@pytest.mark.asyncio
async def test_partial_fill_opens_partial_filled_position_only_executed():
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(making="14.00", taking="40.00")
    with patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(_finding("YES"), _gate(), _risk(), [])
    assert pos["shares"] == 40.0 and pos["position_usd"] == 14.0   # remaining dead; cancel YOK

@pytest.mark.asyncio
async def test_zero_fill_with_order_id_no_position_blocks_submitted_unknown():
    import execution.order_intent as oi
    finding = _finding("YES"); token_id = finding["yes_token_id"]; db_path = str(oi.DB_FILE)
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(status="matched", taking="0", making="0", oid="ord-x")
    with patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(finding, _gate(), _risk(), [])
    assert pos is None
    c = sqlite3.connect(db_path)
    st = c.execute("SELECT status FROM order_intents WHERE market_token_id=?", (token_id,)).fetchone()[0]
    n  = c.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    c.close()
    assert st == "SUBMITTED_UNKNOWN" and n == 0   # bloklayıcı araf, position yok (D2)

@pytest.mark.asyncio
async def test_cost_missing_is_recovery_no_position(caplog):
    import execution.order_intent as oi
    finding = _finding("YES"); token_id = finding["yes_token_id"]; db_path = str(oi.DB_FILE)
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(taking="40.00", making=None)   # shares var, cost yok
    with caplog.at_level(logging.CRITICAL, logger="execution.clob_executor"), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(finding, _gate(), _risk(), [])
    assert pos is None
    c = sqlite3.connect(db_path)
    st = c.execute("SELECT status, reconciliation_reason FROM order_intents WHERE market_token_id=?", (token_id,)).fetchone()
    n  = c.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    c.close()
    assert st[0] == "RECOVERY_REQUIRED" and st[1] == "FILL_COST_MISSING" and n == 0   # D3
    assert any(r.levelno >= logging.CRITICAL for r in caplog.records)

@pytest.mark.asyncio
async def test_resting_status_is_invariant_breach_recovery(caplog):
    import execution.order_intent as oi
    finding = _finding("YES"); token_id = finding["yes_token_id"]; db_path = str(oi.DB_FILE)
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(status="live", taking="0", making="0", oid="ord-x")
    with caplog.at_level(logging.CRITICAL, logger="execution.clob_executor"), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(finding, _gate(), _risk(), [])
    assert pos is None
    c = sqlite3.connect(db_path)
    st = c.execute("SELECT status FROM order_intents WHERE market_token_id=?", (token_id,)).fetchone()[0]
    c.close()
    assert st == "RECOVERY_REQUIRED"
    assert any(r.levelno >= logging.CRITICAL for r in caplog.records)

@pytest.mark.asyncio
async def test_confirm_db_fail_triggers_recovery_then_killswitch(caplog, monkeypatch):
    """confirm_fill_atomic DB fail → recovery_ladder: RECOVERY_REQUIRED dener; o da fail ederse
    emergency_pause (kill-switch) + CRITICAL; position yazılmaz; execute None."""
    import execution.order_intent as oi
    finding = _finding("YES"); db_path = str(oi.DB_FILE)
    fc = MagicMock(); fc.create_market_order.return_value = MagicMock()
    fc.post_order.return_value = _resp(making="25.00", taking="71.43")
    confirm_boom = AsyncMock(side_effect=sqlite3.OperationalError("disk I/O error"))
    pause_spy = AsyncMock()
    with caplog.at_level(logging.CRITICAL, logger="execution.clob_executor"), \
         patch("execution.order_intent.confirm_fill_atomic", confirm_boom), \
         patch("execution.order_intent.transition", new_callable=AsyncMock,
               side_effect=sqlite3.OperationalError("recovery write fail")), \
         patch("execution.clob_executor.set_emergency_pause", pause_spy), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fc):
        from execution.clob_executor import execute
        pos = await execute(finding, _gate(), _risk(), [])
    assert pos is None
    pause_spy.assert_awaited()                       # son kilit: kill-switch denendi
    assert any(r.levelno >= logging.CRITICAL for r in caplog.records)
```

- [ ] **Step 2: Run → FAIL** — başarılı response halen eski inline mantıkla işleniyor; classify_fak_fill/confirm_fill_atomic/recovery_ladder bağlı değil.

- [ ] **Step 3: Minimal wiring** (`clob_executor.py`) — eski `_get/matched/fill_shares` inline bloğu (satır ~339-386) yerine:

```python
from execution.emergency_pause import set_emergency_pause   # üst importlara

async def _recovery_ladder(order_intent_id, reason, slug, order_id=None, size=None):
    """RECOVERY_REQUIRED → kill-switch → son-çare CRITICAL (D5)."""
    try:
        await order_intent.transition(None, order_intent_id, "RECOVERY_REQUIRED",
                                      reason=reason, server_order_id=order_id, size_matched=size)
        logger.critical("[clob] %s: RECOVERY_REQUIRED (%s) intent=%s — 2c-4 reconcile, yeni emir bloklu",
                        slug, reason, order_intent_id)
        return
    except Exception as e1:
        logger.critical("[clob] %s: RECOVERY_REQUIRED write FAIL (%s) — kill-switch deneniyor: %s",
                        slug, reason, e1)
    try:
        await set_emergency_pause(None, reason=f"task_h_recovery_write_failed:{reason}",
                                  source="task_h", order_intent_id=order_intent_id)
        logger.critical("[clob] %s: EMERGENCY_PAUSE set — yeni emir KESİN durdu (%s)", slug, reason)
    except Exception as e2:
        logger.critical("[clob] %s: kill-switch write de FAIL (%s) — is_emergency_paused fail-closed "
                        "son kilit: %s", slug, reason, e2)

# ── post_order başarılı dalı (resp döndü) ──
def _get(o, k, d=None): return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)
decision = order_intent.classify_fak_fill(
    status=_get(resp, "status", ""), taking_amount=_get(resp, "takingAmount", 0),
    making_amount=_get(resp, "makingAmount", None), requested_usd=position_usd,
    order_id=_get(resp, "orderID", None))
kind = decision["kind"]

if kind == "BLOCK_UNKNOWN":
    logger.error("[clob] %s: no_fill_proof (order_id var, fill yok) — SUBMITTED_UNKNOWN kalır (2c-4)",
                 finding["slug"]); return None
if kind == "TERMINAL_ZERO":
    await order_intent.transition(None, order_intent_id, "CANCELLED", reason=decision["reason"])
    return None
if kind == "RECOVERY":
    await _recovery_ladder(order_intent_id, decision["reason"], finding["slug"],
                           order_id=_get(resp, "orderID", None),
                           size=float(decision["shares"]) if decision["shares"] is not None else None)
    return None

# OPEN_FILLED / OPEN_PARTIAL → atomik confirm
position = {
    "position_id": str(uuid4()), "opened_at": datetime.now(timezone.utc).isoformat(),
    "asset": finding["asset"], "action": action, "slug": finding["slug"],
    "pm_entry_price": float(decision["fill_price"]), "fair_value": finding["fair_value"],
    "ref_price": finding["ref_price"], "edge": finding["edge"],
    "position_usd": float(decision["spent_usd"]), "kelly_f": risk_result["kelly_f"],
    "confidence_score": gate_result["confidence_score"], "shares": float(decision["shares"]),
    "order_id": _get(resp, "orderID", ""), "yes_token_id": finding.get("yes_token_id"),
    "no_token_id": finding.get("no_token_id"), "entry_hl_price": finding.get("cur_price"),
    "requires_human_approval": False, "dry_run": False, "status": "open",
    "fill_price": float(decision["fill_price"]), "order_intent_id": order_intent_id,
}
try:
    res = await order_intent.confirm_fill_atomic(None, order_intent_id, position, decision["state"])
except Exception as e:
    await _recovery_ladder(order_intent_id, "CONFIRM_TX_FAILED", finding["slug"],
                           order_id=position["order_id"], size=position["shares"])
    return None
if res == "DUPLICATE":
    logger.error("[clob] %s: confirm DUPLICATE (order_intent_id zaten var) — ikinci position YOK",
                 finding["slug"]); return None
print(f"[clob] {finding['slug']}: FILLED {position['shares']} @ {position['fill_price']} "
      f"(${position['position_usd']}) state={decision['state']}")
return position
```
Not: `position_usd` (istenen) yalnız `classify_fak_fill`'e `requested_usd` olarak geçer; muhasebeye yazılan `position_usd` = `decision["spent_usd"]` (gerçek). `requested` muhasebeye ASLA yazılmaz (D1/D6).

- [ ] **Step 4: Run → PASS** — 6 wiring testi yeşil.

- [ ] **Step 5: Commit** — `feat(P0 Faz2c Task H3): wire execute() fill-confirm — atomic open + recovery ladder`

---

### Task H4: main_loop çift DB yazımını kaldır, telemetri/notify koru

**Files:**
- Modify: `main_loop.py` (`_scan_and_execute`, ~238-260)
- Test: `tests/test_task_h_fill_confirm.py`

- [ ] **Step 1: Failing test — execute tek yazar, main_loop ikinci kez yazmaz, notify korunur**

```python
@pytest.mark.asyncio
async def test_mainloop_does_not_double_write_but_keeps_notify(monkeypatch):
    """_scan_and_execute: execute() artık atomik persist ediyor → main_loop log_position_open ile
    İKİNCİ kez positions'a YAZMAZ; ama notify/telemetri çağrısı KORUNUR."""
    import main_loop
    persisted = {"position_id": "p-x", "order_intent_id": "iid-x", "slug": "btc-x",
                 "asset": "BTC", "action": "YES", "shares": 71.43, "position_usd": 25.0,
                 "status": "open", "dry_run": False}
    log_open_spy = AsyncMock()        # eski DB accounting — ÇAĞRILMAMALI
    notify_spy   = MagicMock()        # telemetri/notify — ÇAĞRILMALI
    monkeypatch.setattr(main_loop, "log_position_open", log_open_spy)
    monkeypatch.setattr(main_loop, "execute", AsyncMock(return_value=persisted))
    monkeypatch.setattr(main_loop, "notify_entry", notify_spy, raising=False)
    # ... _scan_and_execute minimal context ile çağrılır (mevcut test fixture deseni) ...
    # await main_loop._scan_and_execute(open_positions=[], closed_today=[], ...)
    log_open_spy.assert_not_called()  # çift DB yazımı KALDIRILDI
    assert notify_spy.called          # görünürlük korunuyor
```
Not: `_scan_and_execute` imzası/context'i mevcut `tests/test_mainloop*.py` fixture deseninden alınır; notify fonksiyonunun gerçek adı koddan doğrulanır (örn. `notify_entry`/`send_telegram`).

- [ ] **Step 2: Run → FAIL** — mevcut kod hâlâ `await log_position_open(conn, position)` çağırıyor.

- [ ] **Step 3: Minimal değişiklik** (`main_loop.py:248`) — DB accounting satırını kaldır, notify/telemetri/log koru:

```python
position = await execute(finding, gate_result, risk_result, open_positions, conn=conn,
                         council_pass_ts=council_pass_ts)
if position:
    # Task H: DB accounting artık execute() içinde ATOMİK (positions + order_intents tek txn).
    # main_loop İKİNCİ kez yazmaz; yalnız görünürlük/bildirim.
    notify_entry(position)                  # telemetri/Telegram — KORUNUR
    open_positions.append(position)
    print(f"[main_loop] açıldı: {position['slug']} shares={position.get('shares')}")
```
(Önceki `await log_position_open(conn, position)` satırı SİLİNİR.)

- [ ] **Step 4: Run → PASS** + canlı muhasebe tek kaynağa indi.

- [ ] **Step 5: Commit** — `refactor(P0 Faz2c Task H4): move position DB accounting into atomic execute(), keep main_loop telemetry`

---

### Task H5: Regresyon + tekrar-işleme duplicate guard

**Files:**
- Test: `tests/test_task_h_fill_confirm.py`, mevcut suite

- [ ] **Step 1: Duplicate-on-repeat test (partial fill + tekrar response işleme)**

```python
@pytest.mark.asyncio
async def test_repeated_response_processing_no_second_position():
    """Aynı intent için confirm iki kez (partial fill response'u tekrar işlenirse) → ikinci position YOK,
    intent zaten terminal (MONOTONIC) → muhasebe tek (D6)."""
    import execution.order_intent as oi
    db = str(oi.DB_FILE)
    iid = await oi.create_intent(None, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await oi.transition(None, iid, "SUBMITTED_UNKNOWN")
    p = {"position_id": "p1", "opened_at": "2026-06-10T12:00:00+00:00", "slug": "btc-x",
         "asset": "BTC", "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
         "ref_price": 95000.0, "edge": 0.2, "position_usd": 14.0, "kelly_f": 0.15,
         "confidence_score": 82.0, "shares": 40.0, "status": "open", "dry_run": 0,
         "order_intent_id": iid, "order_id": "ord"}
    r1 = await oi.confirm_fill_atomic(None, iid, p, "PARTIAL_FILLED")
    r2 = await oi.confirm_fill_atomic(None, iid, {**p, "position_id": "p2"}, "PARTIAL_FILLED")
    assert (r1, r2) == ("OPENED", "DUPLICATE")
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 1
```

- [ ] **Step 2: Run → PASS** (DB UNIQUE + precheck).

- [ ] **Step 3: Tam regresyon** — `pytest tests/test_execute_intent_wiring.py tests/test_clob_executor.py tests/test_emergency_pause.py tests/test_reconciliation.py tests/test_live_exec_lineage.py tests/test_fill_confirm.py tests/test_task_h_fill_confirm.py tests/test_db_schema_migration.py -q` → **tümü yeşil**; özellikle Task E (timeout→SUBMITTED_UNKNOWN), F (connection/unknown→SUBMITTED_UNKNOWN), G (no-match→CANCELLED) bozulmamalı.

- [ ] **Step 4: graphify update + commit** — `graphify update .` → `chore: graphify update — Faz 2c Task H sonrası` (yalnız graphify-out stage).

- [ ] **Step 5: Final commit** — `test(P0 Faz2c Task H5): duplicate-on-repeat guard + full regression green`

---

## Fail-safe davranış tablosu (state / log / recovery)

| Senaryo | execute() | intent state | position | log | recovery |
|---------|-----------|--------------|----------|-----|----------|
| Full fill (making≥req) | position dict | FILLED | yazılır (atomik) | INFO | — |
| Partial fill (0<making<req) | position dict | PARTIAL_FILLED (terminal) | yazılır (partial shares) | INFO | remaining dead; cancel YOK |
| Zero fill, order_id yok | None | CANCELLED (FAK_ZERO_FILL) | yok | INFO | terminal |
| Zero fill, order_id var | None | SUBMITTED_UNKNOWN (bloklayıcı) | yok | ERROR | 2c-4 reconcile |
| status live/delayed/open/resting | None | RECOVERY_REQUIRED | yok | CRITICAL | 2c-4 + invariant breach |
| shares var, cost (making) yok | None | RECOVERY_REQUIRED (FILL_COST_MISSING) | yok | CRITICAL/ERROR | 2c-4 cost backfill |
| confirm txn fail (INSERT/UPDATE) | None | rollback → SUBMITTED_UNKNOWN → RECOVERY_REQUIRED | yok (rollback) | CRITICAL | recovery ladder |
| RECOVERY_REQUIRED write fail | None | (yazılamadı) | yok | CRITICAL | kill-switch (emergency_pause) |
| kill-switch write fail | None | — | yok | CRITICAL | is_emergency_paused fail-closed=True → sonraki execute bloklu |
| duplicate order_intent_id | None ("DUPLICATE") | değişmez (terminal) | ikinci yok | ERROR | UNIQUE + precheck |
| post_order Exception "no orders found" | None | CANCELLED (FAK_ZERO_FILL) | yok | — | Task G ✅ (regresyon) |
| post_order timeout/connection/unknown | None | SUBMITTED_UNKNOWN | yok | WARNING/ERROR | Task E/F ✅ (regresyon) |

---

## Atomicity'yi nasıl KANITLIYORUM

1. **Aynı DB dosyası, tek connection, tek COMMIT:** `confirm_fill_atomic` `BEGIN IMMEDIATE` → INSERT positions → UPDATE order_intents → `COMMIT`; herhangi bir adım raise → `except` `ROLLBACK`. positions ve order_intents aynı `logs/mispricing.db` içinde olduğu için tek transaction ikisini de kapsar.
2. **INSERT-sonrası UPDATE fail enjeksiyonu (Task H2b):** `aiosqlite.Connection.execute` monkeypatch ile `UPDATE order_intents` anında `OperationalError` fırlatılır; ardından ayrı `sqlite3` connection ile readback → `positions` satırı YOK (rollback kanıtı) + intent `SUBMITTED_UNKNOWN` (terminal değil). "INSERT başarılı ama UPDATE fail → zombi position" senaryosunun imkânsızlığı böyle kanıtlanır.
3. **Terminal-intent-without-position imkânsızlığı:** intent terminal UPDATE'i yalnız aynı txn içinde INSERT ile birlikte COMMIT edilir; INSERT olmadan UPDATE tek başına COMMIT edilemez (kod yolu yok). Test: full-fill sonrası her iki tabloda da satır; UPDATE-fail sonrası iki tabloda da satır YOK.

## Duplicate accounting guard — partial fill & repeated processing

- **DB-level:** `ix_positions_order_intent_id` partial UNIQUE → aynı `order_intent_id` ikinci INSERT `IntegrityError`; `confirm_fill_atomic` precheck bunu `"DUPLICATE"` no-op'a çevirir (rollback).
- **App-level:** `confirm_fill_atomic` BEGIN içinde `SELECT 1 FROM positions WHERE order_intent_id=?` precheck → varsa hiç INSERT denemez.
- **MONOTONIC GUARD (mevcut):** terminal intent (FILLED/PARTIAL_FILLED) yeniden transition edilemez → tekrar işlemede intent state de değişmez.
- **Partial fill:** PARTIAL_FILLED terminal; remaining FAK gereği dead; ikinci confirm denemesi (ör. 2c-4 reconcile aynı intent'i görürse) `"DUPLICATE"` döner — partial pozisyon ikiye katlanmaz.
- Test H5 bu üçlü kilidi partial fill + tekrar confirm ile doğrular.

## Task E/F/G regresyon korunması

- Task H yalnız `post_order` **başarılı** (resp döndü) dalını değiştirir; **exception** dalları (Task E timeout, F connection/unknown, G "no orders found") DOKUNULMAZ.
- H3 wiring eski inline `matched/fill_shares` bloğunu değiştirir ama exception `try/except` yapısı korunur.
- H5 Step 3 tam suite (E/F/G dahil) yeşil zorunluluğu; G'nin `_handle_fak_no_match` + CANCELLED transition'ı aynen çalışır.

## main_loop telemetri kaybı olmadan çift yazımın kaldırılması

- Kaldırılan: `await log_position_open(conn, position)` (artık `execute()` atomik yazıyor → tek kaynak).
- Korunan: `notify_entry`/Telegram bildirimi, `open_positions.append`, print/log görünürlüğü, `log_candidate`/shadow telemetri (bunlar execute öncesi/sonrası ayrı akış).
- Test: `log_position_open` spy `assert_not_called`; `notify_entry` spy `called`.

## 2c-4 reconciliation'a bırakılan açık konular

1. **Araf intent çözümü:** `SUBMITTED_UNKNOWN`/`RECOVERY_REQUIRED` intent'lerin `get_trades` heuristic eşlemesiyle (directional + aggregate + dedup + ambiguous; karar fn `596d9a4`) FILLED/PARTIAL/CANCELLED'a resolve edilmesi.
2. **Cost backfill (FILL_COST_MISSING):** shares-bilinen/cost-bilinmeyen RECOVERY intent'lerin gerçek fill price'ının trades'ten doldurulup pozisyon açılması (veya iptal).
3. **FAK resting-order sinyali:** v2 response'unda hangi alanın resting/open remainder gösterdiğinin kesinleştirilmesi; `_RESTING` listesinin doğrulanması.
4. **Kill-switch resolve protokolü:** Task H recovery-ladder son basamağında tetiklenen `emergency_pause`'ın manuel/otomatik resolve akışı.
5. **classify_fill deprecate:** eski `classify_fill` ile yeni `classify_fak_fill` tek kaynağa indirilmesi.

---

## TODO / RISK notes (implementation-time)

- **TODO (H4):** `notify_entry` fonksiyon adı bir VARSAYIMDIR. H4 implementasyonuna başlamadan ÖNCE `main_loop.py`'deki gerçek bildirim/telemetri fonksiyonunun adı read-only doğrulanacak (örn. `notify_entry` / `send_telegram` / `notify_restart` deseni); test spy'ı ve kod düzenlemesi doğru ada göre yapılacak.
- **TODO/RISK (H2b):** Rollback kanıtı testi şu an `aiosqlite.Connection.execute`'i monkeypatch'leyerek `UPDATE order_intents` anında hata enjekte ediyor — bu GENİŞ bir seam (tüm execute çağrılarını sarar, kırılgan). Mümkünse daha DAR ve stabil bir test seam'e indirilecek: ya `confirm_fill_atomic` içinde enjekte edilebilir bir hook, ya sadece UPDATE adımını saran ince bir yardımcı, ya da gerçek bir constraint ihlali (ör. NOT NULL) tetikleyerek INSERT-sonrası rollback'i organik üretmek. Amaç: atomicity invariant'ını implementasyon detayına daha az bağımlı kanıtlamak.

## Self-review (spec coverage)
- D1 → H1 (USD-denominated classify) + H3 (spent_usd muhasebe). ✅
- D2 → H1 (BLOCK_UNKNOWN/RESTING) + H3 (SUBMITTED_UNKNOWN/RECOVERY). ✅
- D3 → H1 (FILL_COST_MISSING) + H3 (recovery, position yok). ✅
- D4 → H0 (shares + partial UNIQUE, migration testleri). ✅
- D5 → H2/H2b (tek-txn, rollback kanıtı) + H4 (main_loop tek kaynak). ✅
- D6 → H2 (DUPLICATE) + H5 (partial + repeated). ✅
- Regresyon E/F/G → H5 Step 3. ✅
