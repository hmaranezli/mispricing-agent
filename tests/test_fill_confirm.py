"""tests/test_fill_confirm.py — Faz 2b-devamı: fill-confirm + partial + monotonic state guard.

FAK/IOC: fill kesin doğrulanmadan position AÇIK SAYILMAZ. Terminal states (FILLED/
PARTIAL_FILLED/CANCELLED/REJECTED) → downgrade YASAK (monotonic). live=0, canlı emir yok.
"""
import sys
import os
import aiosqlite
import pytest
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── classify_fill (saf) — FAK response → state/executed_size/reason ─────────

def test_classify_zero_fill_cancelled():
    from execution.order_intent import classify_fill
    st, exe, reason = classify_fill(status="matched", taking_amount=0, requested_size=100)
    assert st == "CANCELLED" and exe == 0.0 and reason == "FAK_ZERO_FILL"
    # unmatched de zero-fill
    st2, _, r2 = classify_fill(status="unmatched", taking_amount=None, requested_size=100)
    assert st2 == "CANCELLED" and r2 == "FAK_ZERO_FILL"


def test_classify_partial_fill():
    from execution.order_intent import classify_fill
    st, exe, reason = classify_fill(status="matched", taking_amount=30, requested_size=100)
    assert st == "PARTIAL_FILLED" and exe == 30.0


def test_classify_full_fill():
    from execution.order_intent import classify_fill
    st, exe, reason = classify_fill(status="matched", taking_amount=100, requested_size=100)
    assert st == "FILLED" and exe == 100.0


def test_classify_accepted_no_fill_proof():
    from execution.order_intent import classify_fill
    # status accepted/live, taking belirsiz → ACCEPTED (fill kanıtı yok, 2c reconcile)
    st, exe, reason = classify_fill(status="live", taking_amount=None, requested_size=100,
                                    order_id="srv-1")
    assert st == "ACCEPTED" and exe == 0.0 and reason == "no_fill_proof"


def test_classify_timeout_submitted_unknown():
    from execution.order_intent import classify_fill
    st, exe, reason = classify_fill(status=None, taking_amount=None, requested_size=100,
                                    exception=True)
    assert st == "SUBMITTED_UNKNOWN" and exe == 0.0 and reason == "timeout"


# ── Monotonic state guard — terminal downgrade YASAK ────────────────────────

@pytest.mark.asyncio
async def test_monotonic_guard_blocks_terminal_downgrade():
    from db.schema import init_schema
    import execution.order_intent as oi
    d = tempfile.mkdtemp(); dbp = Path(d) / "t.db"
    conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
    iid = await oi.create_intent(dbp, token_id="t", side="BUY", intended_price=0.5,
                                 intended_size=100.0, slug="s")
    await oi.transition(dbp, iid, "FILLED", size_matched=100.0)
    # FILLED (terminal) → ACCEPTED downgrade YASAK (geç gelen REST/ACCEPTED geri çekemez)
    await oi.transition(dbp, iid, "ACCEPTED", server_order_id="late")
    conn = await aiosqlite.connect(str(dbp))
    async with conn.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)) as c:
        row = await c.fetchone()
    await conn.close()
    assert row[0] == "FILLED", f"terminal FILLED korunmalı, downgrade reddedilmeli: {row[0]}"


@pytest.mark.asyncio
async def test_monotonic_guard_blocks_partial_and_cancelled_downgrade():
    from db.schema import init_schema
    import execution.order_intent as oi
    for terminal in ("PARTIAL_FILLED", "CANCELLED", "REJECTED"):
        d = tempfile.mkdtemp(); dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        iid = await oi.create_intent(dbp, token_id="t", side="BUY", intended_price=0.5,
                                     intended_size=100.0, slug="s")
        await oi.transition(dbp, iid, terminal)
        await oi.transition(dbp, iid, "ACCEPTED")  # downgrade denemesi
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT status FROM order_intents WHERE order_intent_id=?", (iid,)) as c:
            st = (await c.fetchone())[0]
        await conn.close()
        assert st == terminal, f"{terminal}→ACCEPTED downgrade engellenmel: {st}"


def test_is_terminal_helper():
    from execution.order_intent import is_terminal
    for t in ("FILLED", "PARTIAL_FILLED", "CANCELLED", "REJECTED"):
        assert is_terminal(t) is True
    for nt in ("INTENT_CREATED", "SUBMITTED_UNKNOWN", "ACCEPTED", "RECOVERY_REQUIRED"):
        assert is_terminal(nt) is False
