"""execution/order_intent.py — Faz 2a: local idempotency + order intent state machine.

Polymarket CLOB native idempotency YOK (salt random → server dedup yok, client_order_id yok).
Bu yüzden LOCAL idempotency: pre-submit INTENT_CREATED kaydı (DB UNIQUE) + state machine.
Çekirdek invariantlar:
  - Network'e emir gitMEDEN ÖNCE intent DB'ye yazılır (order_intent_id UNIQUE).
  - SUBMITTED_UNKNOWN / RECOVERY_REQUIRED varken aynı token için yeni emir YASAK.
  - Fill kesin doğrulanmadan (FILLED/PARTIAL_FILLED) position AÇIK SAYILMAZ.
Heuristic reconciliation (get_trades eşleme) = Faz 2c. Burada alanlar + state base.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite

from db.logger import DB_FILE

# Faz 2c Task H2 — FAK BUY tamlık eşiği (dust): makingAmount + bu tolerans ≥ requested → FULL.
# USD bazında, Decimal (float epsilon YASAK). Magic number değil, isimli sabit.
FILL_DUST_TOLERANCE_USD = Decimal("0.000001")
# FAK/IOC için resting/open = invariant breach (FAK dinlenemez) → RECOVERY.
_RESTING_STATUSES = ("live", "delayed", "open", "resting")

# State machine
STATES = (
    "INTENT_CREATED", "SUBMITTED_UNKNOWN", "ACCEPTED",
    "PARTIAL_FILLED", "FILLED", "CANCELLED", "REJECTED", "RECOVERY_REQUIRED",
)
OPEN_STATES = frozenset({"FILLED", "PARTIAL_FILLED"})        # position açık SAYILIR
UNRESOLVED_STATES = frozenset({"SUBMITTED_UNKNOWN", "RECOVERY_REQUIRED"})  # yeni emir BLOK
# Faz 2b FAK/IOC final execution states — terminal'e ULAŞAN intent GERİ ÇEKİLEMEZ (monotonic).
TERMINAL_STATES = frozenset({"FILLED", "PARTIAL_FILLED", "CANCELLED", "REJECTED"})


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES


def classify_fill(status, taking_amount, requested_size, order_id=None, exception=False):
    """FAK/IOC response → (state, executed_size, reason). Fill kesin değilse position açılmaz.
      - exception (timeout/network) → SUBMITTED_UNKNOWN (araf, 2c reconcile)
      - matched + taking>0: >=requested → FILLED, else PARTIAL_FILLED (kalan FAK gereği ölü)
      - matched/unmatched + taking==0 → CANCELLED (FAK_ZERO_FILL) — reject DEĞİL
      - accepted/live + fill kanıtı yok → ACCEPTED (no_fill_proof; position YOK, 2c reconcile)
    """
    if exception:
        return ("SUBMITTED_UNKNOWN", 0.0, "timeout")
    s = (status or "").lower()
    taking = float(taking_amount or 0)
    if s == "matched" and taking > 0:
        # FAK kısmi: executed < requested → PARTIAL_FILLED (kalan hayali değil, ölü)
        if taking >= float(requested_size) * 0.999:
            return ("FILLED", taking, None)
        return ("PARTIAL_FILLED", taking, None)
    if s in ("matched", "unmatched") or taking == 0:
        if s in ("live", "delayed", "accepted") or order_id:
            return ("ACCEPTED", 0.0, "no_fill_proof")
        return ("CANCELLED", 0.0, "FAK_ZERO_FILL")
    if s in ("live", "delayed", "accepted") or order_id:
        return ("ACCEPTED", 0.0, "no_fill_proof")
    return ("CANCELLED", 0.0, "FAK_ZERO_FILL")


def classify_fak_fill(status, taking_amount, making_amount, requested_usd, order_id=None):
    """Faz 2c Task H2 — FAK BUY response → karar nesnesi. SAF/sync, DB'ye DOKUNMAZ.

    Sözleşme:
      - USD-denominated (D1): FULL↔PARTIAL kararı YALNIZ makingAmount(harcanan) vs requested_usd
        ile verilir. takingAmount shares'tır; USD hesabına KATILMAZ (yalnız `shares` olarak korunur).
      - Tolerance (dust): makingAmount + FILL_DUST_TOLERANCE_USD ≥ requested_usd → FULL, değilse PARTIAL.
      - Cost yoksa position yok (D3): shares var ama makingAmount yok/≤0 → RECOVERY (FILL_COST_MISSING).
      - Resting/open = FAK invariant breach (D2/D6) → RECOVERY; recovery İŞLEMİ burada ÇAĞRILMAZ.
      - Parasal alanlar Decimal döner (float değil).

    Returns dict: kind, state, shares (Decimal|None), spent_usd (Decimal|None),
                  fill_price (Decimal|None), reason.
    """
    status_norm = str(status).strip().lower()
    taking = Decimal(str(taking_amount if taking_amount is not None else 0))
    making = None if making_amount is None else Decimal(str(making_amount))
    req    = Decimal(str(requested_usd))

    # 1) FAK invariant breach: emir dinleniyor/açık → RECOVERY (D2/D6). EN ÖNCE.
    if status_norm in _RESTING_STATUSES:
        return dict(kind="RECOVERY", state="RECOVERY_REQUIRED", shares=None,
                    spent_usd=None, fill_price=None, reason="FAK_INVARIANT_BREACH_RESTING")

    # 2) Fill kanıtı (shares) yok
    if taking <= 0:
        if order_id:   # order_id var ama fill kanıtı yok → araf (bloklayıcı), filled SAYILMAZ
            return dict(kind="BLOCK_UNKNOWN", state="SUBMITTED_UNKNOWN", shares=None,
                        spent_usd=None, fill_price=None, reason="no_fill_proof")
        return dict(kind="TERMINAL_ZERO", state="CANCELLED", shares=Decimal("0"),
                    spent_usd=Decimal("0"), fill_price=None, reason="FAK_ZERO_FILL")

    # 3) shares var ama cost (makingAmount) yok → cost UYDURULMAZ (D3) → RECOVERY
    if making is None or making <= 0:
        return dict(kind="RECOVERY", state="RECOVERY_REQUIRED", shares=taking,
                    spent_usd=None, fill_price=None, reason="FILL_COST_MISSING")

    # 4) Fill var + cost var → USD bazında tamlık (taking USD hesabına GİRMEZ)
    fill_price = (making / taking).quantize(Decimal("0.000001"))
    if making + FILL_DUST_TOLERANCE_USD >= req:
        return dict(kind="OPEN_FILLED", state="FILLED", shares=taking,
                    spent_usd=making, fill_price=fill_price, reason=None)
    return dict(kind="OPEN_PARTIAL", state="PARTIAL_FILLED", shares=taking,
                spent_usd=making, fill_price=fill_price, reason=None)


def make_order_intent_id() -> str:
    return str(uuid.uuid4())


def payload_hash(token_id, side, price, size) -> str:
    """Deterministik order payload kimliği (audit + duplicate tespiti)."""
    raw = f"{token_id}|{side}|{price}|{size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def is_position_open(status: str) -> bool:
    """Fill-confirm invariant — yalnızca FILLED/PARTIAL_FILLED açık. ACCEPTED ≠ açık."""
    return status in OPEN_STATES


async def create_intent(db_path, token_id, side, intended_price, intended_size,
                        slug=None, wallet=None):
    """PRE-SUBMIT: order_intent_id üret + INTENT_CREATED kaydı (network'ten ÖNCE).
    DB UNIQUE → aynı intent iki kez yazılamaz. Returns order_intent_id."""
    iid = make_order_intent_id()
    now = datetime.now(timezone.utc).isoformat()
    ph = payload_hash(token_id, side, intended_price, intended_size)
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        await conn.execute(
            """INSERT INTO order_intents (
                   order_intent_id, slug, market_token_id, side, intended_price,
                   intended_size, payload_hash, status, intent_timestamp,
                   wallet_address, created_at, updated_at
               ) VALUES (?,?,?,?,?,?,?,'INTENT_CREATED',?,?,?,?)""",
            (iid, slug, token_id, side, intended_price, intended_size, ph, now,
             wallet, now, now),
        )
        await conn.commit()
    return iid


async def transition(db_path, order_intent_id, new_state, server_order_id=None,
                     matched_trade_id=None, size_matched=None, reason=None,
                     submitted_at=None):
    """State geçişi + reconciliation/fill alanları. Bilinmeyen state → hata (whitelist)."""
    if new_state not in STATES:
        raise ValueError(f"geçersiz state: {new_state}")
    now = datetime.now(timezone.utc).isoformat()
    # MONOTONIC GUARD: terminal state'e ulaşmış intent GERİ ÇEKİLEMEZ (geç REST/ACCEPTED/WS).
    # FILLED/PARTIAL_FILLED/CANCELLED/REJECTED → yeni transition strict BLOK.
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        async with conn.execute(
            "SELECT status FROM order_intents WHERE order_intent_id=?", (order_intent_id,)) as cur:
            cur_row = await cur.fetchone()
    if cur_row and is_terminal(cur_row[0]) and cur_row[0] != new_state:
        print(f"[order_intent] MONOTONIC BLOCK: {cur_row[0]} (terminal) → {new_state} reddedildi "
              f"(intent={order_intent_id})")
        return
    sets = ["status=?", "updated_at=?"]
    vals = [new_state, now]
    if server_order_id is not None:
        sets.append("exchange_order_id=?"); vals.append(server_order_id)
    if matched_trade_id is not None:
        sets.append("matched_trade_id=?"); vals.append(matched_trade_id)
    if size_matched is not None:
        sets.append("size_matched=?"); vals.append(size_matched)
    if reason is not None:
        sets.append("reconciliation_reason=?"); vals.append(reason)
    if new_state in UNRESOLVED_STATES:
        sets.append("reconciliation_status=?"); vals.append("pending")
    if submitted_at is not None:
        sets.append("submitted_at=?"); vals.append(submitted_at)
    vals.append(order_intent_id)
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        await conn.execute(
            f"UPDATE order_intents SET {', '.join(sets)} WHERE order_intent_id=?", vals)
        await conn.commit()


async def has_unresolved_intent(db_path, token_id) -> bool:
    """Aynı token için çözülmemiş (SUBMITTED_UNKNOWN/RECOVERY_REQUIRED) intent var mı?
    Varsa yeni emir BLOKLANIR (timeout sonrası otomatik 2. submit YASAK)."""
    qmarks = ",".join("?" * len(UNRESOLVED_STATES))
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        async with conn.execute(
            f"SELECT COUNT(*) FROM order_intents WHERE market_token_id=? AND status IN ({qmarks})",
            (token_id, *sorted(UNRESOLVED_STATES)),
        ) as cur:
            return (await cur.fetchone())[0] > 0
