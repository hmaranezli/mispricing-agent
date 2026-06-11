"""tests/test_task_h_fill_confirm.py — Faz 2c Task H2: classify_fak_fill (saf fonksiyon).

classify_fak_fill = FAK BUY response → karar nesnesi. USD-denominated (D1), cost yoksa
position yok (D3), resting/open = FAK invariant breach (D2/D6). SAF fonksiyon — DB read/write
YOK, execute() wiring YOK, recovery/emergency_pause çağrısı YOK.

RED turu: fonksiyon stub (`raise NotImplementedError`); GREEN davranışı henüz yazılmadı.
"""
import sqlite3
from decimal import Decimal

import aiosqlite
import pytest

from db.schema import init_schema
from execution.order_intent import (classify_fak_fill as C, confirm_fill_atomic,
                                     create_intent, transition)


# 1) FULL_FILL — USD bazında: making (harcanan) requested'i karşılıyor → FILLED
def test_full_fill_usd_denominated():
    d = C(status="matched", taking_amount="71.43", making_amount="25.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_FILLED" and d["state"] == "FILLED"
    assert d["shares"] == Decimal("71.43")          # shares AYRI korunur (takingAmount'tan)
    assert d["spent_usd"] == Decimal("25.00")
    assert d["fill_price"] == (Decimal("25.00") / Decimal("71.43")).quantize(Decimal("0.000001"))


# 2) PARTIAL_FILL — 0 < making < requested → PARTIAL; taking USD gibi yorumlanmaz
def test_partial_fill_usd_denominated():
    d = C(status="matched", taking_amount="40.00", making_amount="14.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED"
    assert d["shares"] == Decimal("40.00") and d["spent_usd"] == Decimal("14.00")


# 3a) NO_FILL — taking=0, order_id YOK → terminal CANCELLED (FAK_ZERO_FILL), position yok
def test_zero_fill_no_order_id_is_terminal_cancelled():
    d = C(status="unmatched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id=None)
    assert d["kind"] == "TERMINAL_ZERO" and d["state"] == "CANCELLED"
    assert d["reason"] == "FAK_ZERO_FILL"


# 3b) NO_FILL_PROOF — order_id/accepted var ama fill kanıtı yok → bloklayıcı, position SİNYALİ YOK
def test_zero_fill_with_order_id_blocks_submitted_unknown():
    d = C(status="matched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id="ord-x")
    assert d["kind"] == "BLOCK_UNKNOWN" and d["state"] == "SUBMITTED_UNKNOWN"
    assert d["kind"] not in ("OPEN_FILLED", "OPEN_PARTIAL")   # position açma sinyali DEĞİL


# 4) COST_MISSING — shares var ama making/cost yok → RECOVERY (FILL_COST_MISSING); cost UYDURULMAZ
def test_shares_present_but_cost_missing_is_recovery():
    d = C(status="matched", taking_amount="40.00", making_amount=None,
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
    assert d["reason"] == "FILL_COST_MISSING"
    assert d["shares"] == Decimal("40.00")
    assert d["spent_usd"] is None                            # cost UYDURULMAZ


# 5) BREACH/INVARIANT — live/delayed/open/resting → recovery/blocking; recovery ÇAĞRILMAZ (saf)
@pytest.mark.parametrize("st", ["live", "delayed", "open", "resting"])
def test_resting_status_is_invariant_breach_recovery(st):
    d = C(status=st, taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id="ord-x")
    assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
    assert "INVARIANT_BREACH" in d["reason"]
    assert d["kind"] not in ("OPEN_FILLED", "OPEN_PARTIAL")  # filled SAYILMAZ


# 6) SHARES_VS_USD CONFUSION — büyük taking full fill yapmaz; karar making(USD) ile verilir
def test_large_shares_small_cost_is_partial_not_full():
    # 1000 shares dolu ama yalnız 10 USD harcandı, requested 25 USD → USD bazında PARTIAL
    d = C(status="matched", taking_amount="1000.0", making_amount="10.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED", (
        "büyük takingAmount FILLED yapmamalı — karar makingAmount(USD) ile verilmeli")
    assert d["shares"] == Decimal("1000.0")     # shares korunur
    assert d["spent_usd"] == Decimal("10.00")   # ama tamlık USD bazında PARTIAL


# 7) TYPE SAFETY — parasal alanlar Decimal döner (float DEĞİL)
def test_monetary_fields_are_decimal_not_float():
    d = C(status="matched", taking_amount="40.00", making_amount="14.00",
          requested_usd="25.00", order_id="ord")
    for k in ("shares", "spent_usd", "fill_price"):
        assert isinstance(d[k], Decimal), f"{k} Decimal olmalı, float DEĞİL: {type(d[k])}"
        assert not isinstance(d[k], float)
    # Exact Decimal aritmetiği: 14.00/40.00 = 0.35 → quantize 0.350000
    assert d["fill_price"] == Decimal("0.350000")


# ── Ek RED turu: rounding/tolerance (epsilon) davranışı ──────────────────────

# 8) Near-full fill tolerance: making requested'e çok yakın (tolerans içinde) → FULL_FILL
def test_near_full_fill_within_tolerance_is_full():
    d = C(status="filled", taking_amount="28.57", making_amount=Decimal("9.99999999"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_FILLED" and d["state"] == "FILLED", (
        "tolerans içindeki near-full (9.99999999/10.00) FULL_FILL sayılmalı")
    assert d["spent_usd"] == Decimal("9.99999999")


# 9) Real partial must remain partial: making tolerans ALTINDA → PARTIAL_FILL
def test_real_partial_below_tolerance_stays_partial():
    d = C(status="filled", taking_amount="28.28", making_amount=Decimal("9.90"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED", (
        "tolerans altındaki gerçek partial (9.90/10.00) PARTIAL kalmalı")
    assert d["spent_usd"] == Decimal("9.90")


# 10) Tolerance Decimal olmalı (float epsilon DEĞİL); parasal alanlar Decimal kalmalı
def test_tolerance_is_decimal_not_float_epsilon():
    d = C(status="filled", taking_amount="28.57", making_amount=Decimal("9.99999999"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_FILLED"
    for k in ("shares", "spent_usd", "fill_price"):
        assert isinstance(d[k], Decimal) and not isinstance(d[k], float), (
            f"{k} Decimal olmalı (float epsilon yasak): {type(d[k])}")


# 11) Status normalization: "FILLED" == "filled" → aynı sınıflandırma (case-insensitive)
def test_status_normalization_uppercase_equals_lowercase():
    args = dict(taking_amount="28.57", making_amount=Decimal("10.00"),
                requested_usd=Decimal("10.00"), order_id="ord")
    up = C(status="FILLED", **args)
    lo = C(status="filled", **args)
    assert up["kind"] == lo["kind"] == "OPEN_FILLED"
    assert up["state"] == lo["state"] == "FILLED"
    assert up == lo, f"case farkı aynı sonucu vermeli: {up} != {lo}"


# ════════════════════════════════════════════════════════════════════════════
# Task H3 — confirm_fill_atomic RED turu (helper + happy/duplicate/insert-fail/
# IntegrityError-readback). H3b (UPDATE-after-INSERT rollback) AYRI tasktır, BURADA YOK.
#
# Sözleşme: confirm_fill_atomic(db_path, order_intent_id, position_row, terminal_state).
#   - position_row + terminal_state alır; H2 decision dict'ini DOĞRUDAN almaz.
#   - classify_fak_fill çağrısı / making/taking/requested_usd hesabı YOK (muhasebe H2'de bitti).
#   - terminal_state whitelist yalnız FILLED / PARTIAL_FILLED.
#   - Tüm testler EXPLICIT tmp DB kullanır (gerçek init_schema); canlı DB'ye yazmaz.
#
# RED turu: confirm_fill_atomic STUB → NotImplementedError. GREEN davranışı henüz yok.
# (Aşağıdaki monkeypatch seam'leri GREEN'de tetiklenecek; RED'de stub önce raise eder.)
# ════════════════════════════════════════════════════════════════════════════

async def _make_db(tmp_path):
    """Gerçek schema/migration ile kurulmuş per-test tmp DB (canlı DB DEĞİL)."""
    db = tmp_path / "h3.db"
    conn = await aiosqlite.connect(str(db))
    await init_schema(conn)
    await conn.close()
    return str(db)


def _posrow(oiid, pid="pos-1", **over):
    """H4 wiring'in kuracağı position_row'un manuel/sabit eşdeğeri (mapping testlenmez)."""
    row = {"position_id": pid, "opened_at": "2026-06-10T12:00:00+00:00", "slug": "btc-x",
           "asset": "BTC", "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
           "ref_price": 95000.0, "edge": 0.2, "position_usd": 25.0, "kelly_f": 0.15,
           "confidence_score": 82.0, "shares": 71.43, "dry_run": 0, "status": "open",
           "order_intent_id": oiid, "order_id": "ord"}
    row.update(over)
    return row


# H3-1) FULL_FILL — position INSERT + order_intents FILLED aynı transaction'da atomik
@pytest.mark.asyncio
async def test_confirm_full_fill_writes_position_and_terminal_intent_atomically(tmp_path):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    res = await confirm_fill_atomic(db, iid, _posrow(iid, shares=71.43), "FILLED")
    assert res == "OPENED"
    c = sqlite3.connect(db)
    prow = c.execute("SELECT order_intent_id, shares FROM positions WHERE order_intent_id=?",
                     (iid,)).fetchone()
    irow = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()
    c.close()
    assert prow == (iid, 71.43), f"position lineage+shares yazılmalı: {prow}"
    assert irow[0] == "FILLED", f"intent terminal FILLED olmalı: {irow}"


# H3-2) PARTIAL_FILL — position INSERT + order_intents PARTIAL_FILLED aynı transaction'da atomik
@pytest.mark.asyncio
async def test_confirm_partial_fill_writes_position_and_terminal_intent_atomically(tmp_path):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    res = await confirm_fill_atomic(db, iid, _posrow(iid, shares=40.0, position_usd=14.0),
                                    "PARTIAL_FILLED")
    assert res == "OPENED"
    c = sqlite3.connect(db)
    prow = c.execute("SELECT order_intent_id, shares FROM positions WHERE order_intent_id=?",
                     (iid,)).fetchone()
    irow = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()
    c.close()
    assert prow == (iid, 40.0), f"partial position lineage+shares: {prow}"
    assert irow[0] == "PARTIAL_FILLED", f"intent terminal PARTIAL_FILLED olmalı: {irow}"


# H3-3) DUPLICATE — aynı order_intent_id ikinci confirm → app precheck → DUPLICATE no-op
@pytest.mark.asyncio
async def test_duplicate_intent_second_confirm_is_noop_readback_proof(tmp_path):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    r1 = await confirm_fill_atomic(db, iid, _posrow(iid, "pos-1"), "FILLED")
    r2 = await confirm_fill_atomic(db, iid, _posrow(iid, "pos-2"), "FILLED")   # tekrar
    assert (r1, r2) == ("OPENED", "DUPLICATE"), f"ikinci confirm DUPLICATE olmalı: {(r1, r2)}"
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 1, f"ikinci position AÇILMAMALI (readback proof): {n}"


# H3-4) IntegrityError + readback EXISTING → DUPLICATE (precheck'i aşan race simülasyonu)
@pytest.mark.asyncio
async def test_integrity_error_readback_existing_duplicate_is_noop(tmp_path, monkeypatch):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    # Zaten yazılmış bir position (başka bir confirm/yarış) → INSERT UNIQUE'e çarpacak.
    pre = sqlite3.connect(db)
    pre.execute("INSERT INTO positions (position_id, ts_open, slug, asset, action, status, "
                "dry_run, order_intent_id) VALUES (?,?,?,?,?,?,?,?)",
                ("pre-1", "2026-06-10T12:00:00+00:00", "btc-x", "BTC", "YES", "open", 0, iid))
    pre.commit(); pre.close()
    # Race penceresi: İLK positions/order_intent_id SELECT'i (precheck) boş döndür → INSERT denenir.
    # GREEN sözleşmesi: precheck ile readback ayırt edilebilir SELECT'ler olmalı (readback patch'lenmez).
    real_execute = aiosqlite.Connection.execute
    seen = {"precheck": False}

    async def _bypass_precheck(self, sql, *a, **k):
        s = " ".join(str(sql).split()).upper()
        if (not seen["precheck"] and s.startswith("SELECT")
                and "POSITIONS" in s and "ORDER_INTENT_ID" in s):
            seen["precheck"] = True
            return await real_execute(self, "SELECT 1 WHERE 0")   # precheck hiçbir şey görmez
        return await real_execute(self, sql, *a, **k)

    monkeypatch.setattr(aiosqlite.Connection, "execute", _bypass_precheck)
    res = await confirm_fill_atomic(db, iid, _posrow(iid, "pos-2"), "FILLED")
    assert res == "DUPLICATE", f"IntegrityError+readback-existing → DUPLICATE olmalı: {res}"
    monkeypatch.undo()
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 1, f"ikinci position yazılmamalı (rollback): {n}"


# H3-5) IntegrityError + readback MISSING → SESSİZCE YUTMA; raise + terminalize ETME
@pytest.mark.asyncio
async def test_integrity_error_readback_missing_raises_and_does_not_terminalize(tmp_path):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    # asset NOT NULL ihlali → gerçek IntegrityError; aynı iid'li position YOK → readback boş.
    bad = _posrow(iid, asset=None)
    with pytest.raises(sqlite3.IntegrityError):
        await confirm_fill_atomic(db, iid, bad, "FILLED")
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    st = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 0, f"IntegrityError readback-missing → position yazılmamalı: {n}"
    assert st == "SUBMITTED_UNKNOWN", f"intent terminalize EDİLMEMELİ (fail-safe): {st}"


# H3-6) INSERT gerçek fail (OperationalError) → rollback; position yok, intent terminal değil
@pytest.mark.asyncio
async def test_insert_fail_rolls_back_no_terminal_intent(tmp_path, monkeypatch):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")
    real_execute = aiosqlite.Connection.execute

    async def _boom_on_insert(self, sql, *a, **k):
        s = " ".join(str(sql).split()).upper()
        if s.startswith("INSERT INTO POSITIONS"):
            raise sqlite3.OperationalError("disk I/O error")   # gerçek INSERT fault
        return await real_execute(self, sql, *a, **k)

    monkeypatch.setattr(aiosqlite.Connection, "execute", _boom_on_insert)
    with pytest.raises(sqlite3.OperationalError):
        await confirm_fill_atomic(db, iid, _posrow(iid), "FILLED")
    monkeypatch.undo()
    c = sqlite3.connect(db)
    n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
    st = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)).fetchone()[0]
    c.close()
    assert n == 0, f"INSERT fail → rollback, position yok: {n}"
    assert st == "SUBMITTED_UNKNOWN", f"intent FILLED/PARTIAL_FILLED OLMAMALI (rollback): {st}"


# ════════════════════════════════════════════════════════════════════════════
# Task H3b — UPDATE-after-INSERT rollback proof (TRIGGER-BASED, ORGANİK FAULT).
# Monkeypatch/driver-patch/test-seam YOK; hata SAF SQLite motorundan (RAISE ABORT) gelir.
# Bu DAR/STABİL seam, H3 RED'deki kırılgan execute-monkeypatch endişesini çözer.
# Klasik RED olmayabilir: H3 generic/IntegrityError rollback doğruysa ilk çalıştırmada PASS
# (regression-lock/proof). INSERT positions başarılı → UPDATE order_intents trigger ile fail
# → tüm txn rollback: position SİLİNİR (zombi yok), intent SUBMITTED_UNKNOWN kalır.
# ════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_update_fail_after_insert_rolls_back_with_sqlite_trigger(tmp_path):
    db = await _make_db(tmp_path)
    iid = await create_intent(db, "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await transition(db, iid, "SUBMITTED_UNKNOWN")     # seed ÖNCE (trigger henüz YOK)

    # Trigger seed'den SONRA kurulur; NORMAL (TEMP DEĞİL) → confirm_fill_atomic'in AYRI
    # connection'ında görünür. Yalnız bu order_intent_id'nin UPDATE'inde RAISE(ABORT).
    setup = sqlite3.connect(db)
    setup.executescript(
        "CREATE TRIGGER inject_update_fail\n"
        "BEFORE UPDATE ON order_intents\n"
        f"WHEN NEW.order_intent_id = '{iid}'\n"
        "BEGIN\n"
        "  SELECT RAISE(ABORT, 'Simulated Update Failure');\n"
        "END;")
    setup.commit()
    setup.close()        # KRİTİK: lock serbest — confirm BEGIN IMMEDIATE 'locked' olmamalı

    try:
        # INSERT positions başarılı olmalı; fail YALNIZ UPDATE order_intents'te (trigger).
        with pytest.raises(sqlite3.DatabaseError) as ei:
            await confirm_fill_atomic(db, iid, _posrow(iid), "FILLED")
        msg = str(ei.value)
        assert "Simulated Update Failure" in msg, f"hata trigger'dan gelmeli (lock değil): {msg!r}"
        assert "database is locked" not in msg.lower(), f"database-is-locked tuzağı: {msg!r}"

        # Readback: rollback gerçek mi?
        c = sqlite3.connect(db)
        n = c.execute("SELECT COUNT(*) FROM positions WHERE order_intent_id=?", (iid,)).fetchone()[0]
        st = c.execute("SELECT status FROM order_intents WHERE order_intent_id=?",
                       (iid,)).fetchone()[0]
        c.close()
        assert n == 0, f"UPDATE fail → INSERT ROLLBACK olmalı (zombi position yok): {n}"
        assert st == "SUBMITTED_UNKNOWN", f"intent terminalize EDİLMEMELİ (rollback): {st}"
    finally:
        # KRİTİK teardown: PASS da FAIL de olsa trigger DÜŞÜRÜLÜR (ayrı connection + commit).
        cleanup = sqlite3.connect(db)
        cleanup.execute("DROP TRIGGER IF EXISTS inject_update_fail")
        cleanup.commit()
        cleanup.close()
