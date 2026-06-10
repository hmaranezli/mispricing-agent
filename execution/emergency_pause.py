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
