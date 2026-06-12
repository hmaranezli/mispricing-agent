"""execution/emergency_pause.py — Faz 2c-2: kill-switch persist + runtime block.

Reconciliation'ın ürettiği emergency_pause=True artık SADECE rapor değil. Burada:
  - DB'de persist edilir (execution_state singleton satır → restart sonrası kalıcı).
  - execute() girişinde okunur → paused ise network call YAPILMAZ.
  - Tetiklenince SCREAM: CRITICAL log (reason/source/order_intent_id) — sessiz ölüm yok.
  - Set IDEMPOTENT: ikinci set mevcut pause'u (ilk reason/source/created_at) BOZMAZ.
  - Okuma FAIL-CLOSED: DB connection/timeout/schema/query hatası → paused say.
  - Otomatik temizlik YASAK → yalnız clear_emergency_pause() (admin/insan onayı).

Bu modül monitor/kill_switch.py'den AYRIDIR: o dosya-tabanlı OPERATÖR kill-switch'i;
bu ise reconciliation tetikli OTOMATİK, DB-persist emergency pause.
"""
import logging
from datetime import datetime, timezone

import aiosqlite

from db.logger import DB_FILE

logger = logging.getLogger("execution.emergency_pause")

_STATE_KEY = "global"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def is_emergency_paused(db_path=None) -> bool:
    """Sistem acil-duraklatmada mı? FAIL-CLOSED: herhangi bir okuma hatası → True (paused).

    DB connection error / timeout / schema yok / query hatası → emin değiliz → DURDUR.
    """
    try:
        async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
            async with conn.execute(
                "SELECT emergency_paused FROM execution_state WHERE state_key=?",
                (_STATE_KEY,),
            ) as cur:
                row = await cur.fetchone()
        return bool(row and row[0])
    except Exception as e:
        # Fail-closed: durumu okuyamıyorsak güvenli taraf = duraklatılmış say.
        logger.critical(
            "[emergency_pause] FAIL-CLOSED — durum okunamadı, paused VARSAYILDI: %s", e)
        return True


async def get_pause_record(db_path=None) -> dict | None:
    """Audit/bildirim için pause kaydı. Okuma hatası → None (karar için is_emergency_paused kullan)."""
    try:
        async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM execution_state WHERE state_key=?", (_STATE_KEY,)) as cur:
                row = await cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.critical("[emergency_pause] get_pause_record okuma hatası: %s", e)
        return None


async def set_emergency_pause(db_path=None, reason=None, source=None,
                              order_intent_id=None) -> None:
    """Acil duraklatmayı set et. IDEMPOTENT: zaten paused ise ilk pause'u BOZMA.

    Tetikleme (False→True) anında SCREAM: CRITICAL log. Otomatik temizlenmez.
    """
    now = _now()
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        async with conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key=?",
            (_STATE_KEY,)) as cur:
            row = await cur.fetchone()
        if row and row[0]:
            # Zaten paused → ilk neden/kaynak/created_at korunur (bozma). Düşük seviye iz.
            logger.warning(
                "[emergency_pause] zaten paused — yeni tetik korundu (reason=%s source=%s "
                "intent=%s); ilk pause bozulmadı", reason, source, order_intent_id)
            return
        # Trip (False→True veya ilk kayıt): UPSERT — created_at burada sabitlenir.
        old_state = row[0] if row else 0
        await conn.execute(
            """INSERT INTO execution_state
                   (state_key, emergency_paused, reason, source, order_intent_id,
                    created_at, updated_at)
               VALUES (?, 1, ?, ?, ?, ?, ?)
               ON CONFLICT(state_key) DO UPDATE SET
                   emergency_paused=1, reason=excluded.reason, source=excluded.source,
                   order_intent_id=excluded.order_intent_id,
                   created_at=excluded.created_at, updated_at=excluded.updated_at""",
            (_STATE_KEY, reason, source, order_intent_id, now, now),
        )
        # Append-only audit (Faz 2c-4 Slice D): YALNIZ başarılı 0→1 geçişinde TEK TRIP event.
        # Idempotent ikinci çağrı yukarıda erken-return ettiği için buraya ulaşmaz → duplicate yok.
        await conn.execute(
            """INSERT INTO execution_state_events
                   (event_type, ts, old_state, new_state, reason, source,
                    order_intent_id, force, verified)
               VALUES ('TRIP', ?, ?, 1, ?, ?, ?, 0, 0)""",
            (now, old_state, reason, source, order_intent_id),
        )
        await conn.commit()
    # SCREAM on death — sessiz kalma.
    logger.critical(
        "[emergency_pause] 🚨 EMERGENCY PAUSE TETİKLENDİ — yeni emir BLOKLU. "
        "reason=%s source=%s order_intent_id=%s", reason, source, order_intent_id)


async def clear_emergency_pause(db_path=None, cleared_by=None, note=None) -> None:
    """MANUEL reset (admin/insan onayı). Otomatik çağrılMAZ — yalnız operatör.

    Audit: reason alanına 'cleared_by:...' yazılır, updated_at güncellenir.
    """
    now = _now()
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        await conn.execute(
            """INSERT INTO execution_state
                   (state_key, emergency_paused, reason, source, updated_at)
               VALUES (?, 0, ?, ?, ?)
               ON CONFLICT(state_key) DO UPDATE SET
                   emergency_paused=0, reason=excluded.reason,
                   source=excluded.source, updated_at=excluded.updated_at""",
            (_STATE_KEY, f"cleared_by:{cleared_by}" + (f" note:{note}" if note else ""),
             "manual_admin", now),
        )
        await conn.commit()
    logger.critical(
        "[emergency_pause] ✅ MANUEL CLEAR — emergency pause kaldırıldı (cleared_by=%s note=%s)",
        cleared_by, note)


async def resolve_emergency_pause(db_path=None, *, order_intent_id, resolved_by, reason,
                                  mode="verified") -> dict:
    """Faz 2c-4 Slice D — emergency_pause resolve protokolü (verified + force path).

    Ortak: offending order_intent durumu DB'den okunur ve `observed_intent_state` olarak audit'e
    korunur. Intent KAYDI YOKSA her iki mode da fail-closed (clear yok, event yok). Clear + RESOLVE
    event TEK transaction / TEK commit; legacy `clear_emergency_pause` ÇAĞRILMAZ (trip alanını ezmez).

      - mode='verified': intent `order_intent.TERMINAL_STATES`'te ise temizler (verified=1, force=0);
        terminal değilse fail-closed (clear yok, event yok).
      - mode='force': intent VARSA terminal önkoşulu BYPASS edilir → operatör override ile temizler
        (force=1, verified=0). Var-olmayan intent yine fail-closed.

    Kapsam dışı (sonraki RED'ler): already-clear/idempotency, empty resolved_by/reason validation,
    audit-failure handling.
    """
    from execution.order_intent import TERMINAL_STATES   # dinamik (circular import yok)
    if mode not in ("verified", "force"):
        raise ValueError(
            f"resolve_emergency_pause yalnız mode='verified'|'force' destekler: {mode!r}")
    now = _now()
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        # Offending intent durumu — minimal SELECT (her iki mode için)
        async with conn.execute(
            "SELECT status FROM order_intents WHERE order_intent_id=?",
            (order_intent_id,)) as cur:
            irow = await cur.fetchone()
        observed = irow[0] if irow else None
        # Intent kaydı YOK → her iki mode fail-closed (force bile var-olmayan intent'i bypass etmez)
        if irow is None:
            logger.critical(
                "[emergency_pause] %s-resolve REDDEDİLDİ — offending intent KAYDI YOK "
                "(intent=%s); pause AKTİF kalır.", mode, order_intent_id)
            return dict(resolved=False, blocked=True, mode=mode, observed_intent_state=None)
        # Verified önkoşul: intent terminal değilse fail-closed. Force bu kontrolü BYPASS eder.
        if mode == "verified" and observed not in TERMINAL_STATES:
            logger.critical(
                "[emergency_pause] verified-resolve REDDEDİLDİ — offending intent terminal değil "
                "(intent=%s observed=%s); pause AKTİF kalır.", order_intent_id, observed)
            return dict(resolved=False, blocked=True, mode="verified",
                        observed_intent_state=observed)
        verified_flag = 1 if mode == "verified" else 0
        force_flag = 1 if mode == "force" else 0
        # Atomik KOŞULLU clear: yalnız gerçek 1→0 geçişinde satır güncellenir (ayrı SELECT→if→UPDATE
        # race'i YOK). rowcount>0 ⇔ pause gerçekten 1'den 0'a indi → idempotency garantisi.
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute(
            "UPDATE execution_state SET emergency_paused=0, updated_at=? "
            "WHERE state_key=? AND emergency_paused=1",
            (now, _STATE_KEY))
        transitioned = cur.rowcount > 0
        if transitioned:
            # SADECE gerçek 1→0 geçişinde RESOLVE event (old_state=1, new_state=0); aynı transaction.
            await conn.execute(
                """INSERT INTO execution_state_events
                       (event_type, ts, old_state, new_state, reason, source,
                        order_intent_id, observed_intent_state, resolved_by, force, verified)
                   VALUES ('RESOLVE', ?, 1, 0, ?, ?, ?, ?, ?, ?, ?)""",
                (now, reason, f"resolve_{mode}", order_intent_id, observed,
                 resolved_by, force_flag, verified_flag))
        await conn.execute("COMMIT")
    if not transitioned:
        # Pause zaten clear → idempotent no-op: yeni RESOLVE event YOK, state değişmedi.
        logger.info(
            "[emergency_pause] %s-resolve no-op — pause zaten clear (intent=%s); event yazılmadı.",
            mode, order_intent_id)
        return dict(resolved=False, already_clear=True, mode=mode,
                    observed_intent_state=observed)
    logger.critical(
        "[emergency_pause] ✅ %s RESOLVE — pause temizlendi (intent=%s observed=%s "
        "resolved_by=%s reason=%s)", mode.upper(), order_intent_id, observed, resolved_by, reason)
    return dict(resolved=True, mode=mode, verified=bool(verified_flag),
                observed_intent_state=observed, old_state=1)
