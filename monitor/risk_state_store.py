"""monitor/risk_state_store.py — E3 risk-state persistence (restart'tan sağ çıkma).

E1b: risk state restart'tan sağ çıkmalı; process-memory-only YASAK. Bu modül risk state'i sqlite'a
JSON payload olarak kalıcılaştırır (tek-satır singleton `state_key='global'`, emergency_pause
pattern'iyle simetrik). Eksik/bozuk/tanınmayan state'te SESSİZCE Operational'a DÜŞMEZ → RiskStateCorruptError.

Dar kapsam: UTC rollover YOK, active_blockers köprüsü YOK, main_loop wiring YOK, async optimizasyon YOK.
sqlite3 sync; yalnız caller'ın verdiği db_path. Eşik/loop semantiği bu modülde değil.
"""
import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict

from monitor.risk_state import reduce_risk_mode

_SCHEMA_VERSION = 1
_STATE_KEY = "global"
_REQUIRED_FIELDS = (
    "trading_day_utc", "start_of_day_equity", "realized_pnl_today",
    "active_blockers", "effective_mode", "updated_at_utc", "schema_version",
)


class RiskStateCorruptError(Exception):
    """Saklı risk state bozuk/eksik/tanınmayan → fail-closed (Operational'a sessiz düşüş YOK)."""


@dataclass
class RiskStateSnapshot:
    trading_day_utc: str
    start_of_day_equity: float
    realized_pnl_today: float
    active_blockers: list
    effective_mode: str
    updated_at_utc: str
    schema_version: int = _SCHEMA_VERSION
    # E3b bootstrap audit metadata (opsiyonel; geriye uyumlu — eski 7-alan kurulum çalışmaya devam eder).
    bootstrap_approved_by: str = None
    bootstrap_reason: str = None


def init_risk_state_store(db_path) -> None:
    """risk_state tablosunu (yoksa) oluştur. Tek-satır singleton; JSON payload."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS risk_state ("
            "state_key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        conn.commit()
    finally:
        conn.close()


def save_risk_state(db_path, snapshot: RiskStateSnapshot) -> None:
    """Snapshot'ı JSON payload olarak singleton satıra UPSERT. Kaydetmeden önce tutarlılık doğrulanır."""
    _validate(asdict(snapshot))   # save tarafında da fail-closed (tutarsız snapshot yazılmaz)
    payload = json.dumps(asdict(snapshot))
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO risk_state (state_key, payload) VALUES (?, ?) "
            "ON CONFLICT(state_key) DO UPDATE SET payload=excluded.payload",
            (_STATE_KEY, payload))
        conn.commit()
    finally:
        conn.close()


def load_risk_state(db_path) -> RiskStateSnapshot:
    """Singleton satırı oku → RiskStateSnapshot. Bozuk/eksik/tanınmayan → RiskStateCorruptError.

    Operational'a SESSİZ düşüş YOK.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT payload FROM risk_state WHERE state_key=?", (_STATE_KEY,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RiskStateCorruptError("risk_state singleton kaydı yok (init/save yapılmadı)")
    try:
        data = json.loads(row[0])
    except (ValueError, TypeError) as e:
        raise RiskStateCorruptError(f"risk_state payload geçersiz JSON: {e}")
    if not isinstance(data, dict):
        raise RiskStateCorruptError("risk_state payload dict değil")
    _validate(data)
    return RiskStateSnapshot(
        trading_day_utc=data["trading_day_utc"],
        start_of_day_equity=data["start_of_day_equity"],
        realized_pnl_today=data["realized_pnl_today"],
        active_blockers=data["active_blockers"],
        effective_mode=data["effective_mode"],
        updated_at_utc=data["updated_at_utc"],
        schema_version=data["schema_version"],
        bootstrap_approved_by=data.get("bootstrap_approved_by"),
        bootstrap_reason=data.get("bootstrap_reason"),
    )


def initialize_day_zero_state(db_path, trading_day_utc, start_of_day_equity,
                              updated_at_utc, approved_by, reason) -> RiskStateSnapshot:
    """E3b — Day-0 explicit, operatör-onaylı risk-state bootstrap.

    YALNIZ caller değerleri (canlı balance/API/config/clock/env/network YOK). İlk geçerli Operational
    snapshot'ı üretir; YALNIZ singleton satır GERÇEKTEN yoksa izinlidir. Mevcut GEÇERLİ state →
    ValueError (sessiz overwrite yok); mevcut BOZUK state → RiskStateCorruptError (her corrupt
    bootstrap-izinli sayılmaz). Audit metadata (approved_by/reason) snapshot'a persist edilir.
    """
    if not isinstance(start_of_day_equity, (int, float)) or isinstance(start_of_day_equity, bool) \
            or start_of_day_equity <= 0:
        raise ValueError(f"start_of_day_equity > 0 olmalı: {start_of_day_equity!r}")
    for _name, _v in (("trading_day_utc", trading_day_utc), ("updated_at_utc", updated_at_utc),
                      ("approved_by", approved_by), ("reason", reason)):
        if not isinstance(_v, str) or not _v.strip():
            raise ValueError(f"{_name} boş olmayan string olmalı: {_v!r}")
    # Mevcut satır var mı? (missing vs present ayrımı — load None'da da raise eder, o yüzden raw bak)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT payload FROM risk_state WHERE state_key=?", (_STATE_KEY,)).fetchone()
    finally:
        conn.close()
    if row is not None:
        # Satır VAR → bootstrap yapma. Geçerliyse ValueError; bozuksa load_risk_state RiskStateCorruptError
        # fırlatır (propagate). Hiçbir durumda overwrite YOK.
        load_risk_state(db_path)   # bozuksa burada RiskStateCorruptError yükselir
        raise ValueError("risk_state zaten initialize edilmiş — bootstrap overwrite etmez")
    snap = RiskStateSnapshot(
        trading_day_utc=trading_day_utc,
        start_of_day_equity=float(start_of_day_equity),
        realized_pnl_today=0.0,
        active_blockers=[],
        effective_mode="Operational",
        updated_at_utc=updated_at_utc,
        schema_version=_SCHEMA_VERSION,
        bootstrap_approved_by=approved_by,
        bootstrap_reason=reason,
    )
    save_risk_state(db_path, snap)
    return snap


def _require_iso_date(name, value) -> None:
    """value strict YYYY-MM-DD ISO tarih string'i olmalı (strptime ile doğrulanır; sistem clock YOK)."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} boş olmayan string olmalı: {value!r}")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{name} strict YYYY-MM-DD olmalı: {value!r}")


def rollover_risk_state_if_new_day(snapshot, current_trading_day_utc,
                                   new_start_of_day_equity, updated_at_utc) -> RiskStateSnapshot:
    """E3c — SAF UTC rollover (snapshot→snapshot). Sistem clock/API/balance/config/DB/save/load YOK.

    same-day → unchanged; new-day → yalnız GÜNLÜK sayaçları sıfırla (daily_loss kaldır, pnl=0, equity/
    updated_at güncelle) ve mod reduce_risk_mode ile yeniden hesapla; kill_switch/halted/manual_review/
    cooldown KORUNUR; audit alanları KORUNUR. backwards day / equity<=0 / boş string → ValueError.
    Tarih karşılaştırması ancak strict YYYY-MM-DD doğrulamasından sonra leksikografik yapılır.
    """
    if not isinstance(new_start_of_day_equity, (int, float)) or isinstance(new_start_of_day_equity, bool) \
            or new_start_of_day_equity <= 0:
        raise ValueError(f"new_start_of_day_equity > 0 olmalı: {new_start_of_day_equity!r}")
    if not isinstance(updated_at_utc, str) or not updated_at_utc.strip():
        raise ValueError(f"updated_at_utc boş olmayan string olmalı: {updated_at_utc!r}")
    _require_iso_date("current_trading_day_utc", current_trading_day_utc)
    _require_iso_date("snapshot.trading_day_utc", snapshot.trading_day_utc)

    if current_trading_day_utc < snapshot.trading_day_utc:
        raise ValueError(
            f"current_trading_day_utc geçmiş olamaz: {current_trading_day_utc} < {snapshot.trading_day_utc}")
    if current_trading_day_utc == snapshot.trading_day_utc:
        return snapshot   # same-day → günlük reset yok, değişmeden döner

    # New day → yalnız daily_loss kaldırılır; diğer blocker'lar (kill_switch/halted/manual_review/cooldown) korunur.
    new_blockers = [b for b in snapshot.active_blockers if b != "daily_loss"]
    return RiskStateSnapshot(
        trading_day_utc=current_trading_day_utc,
        start_of_day_equity=float(new_start_of_day_equity),
        realized_pnl_today=0.0,
        active_blockers=new_blockers,
        effective_mode=reduce_risk_mode(new_blockers),
        updated_at_utc=updated_at_utc,
        schema_version=snapshot.schema_version,
        bootstrap_approved_by=snapshot.bootstrap_approved_by,
        bootstrap_reason=snapshot.bootstrap_reason,
    )


def _validate(data: dict) -> None:
    """Tutarlılık: zorunlu alanlar, schema_version==1, active_blockers list, effective_mode reducer ile
    eşleşir, blocker'lar reduce_risk_mode'dan geçer (bilinmeyen → reddedilir). Hata → RiskStateCorruptError."""
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise RiskStateCorruptError(f"risk_state eksik alan(lar): {missing}")
    if data["schema_version"] != _SCHEMA_VERSION:
        raise RiskStateCorruptError(f"risk_state schema_version beklenmeyen: {data['schema_version']}")
    if not isinstance(data["active_blockers"], list):
        raise RiskStateCorruptError("active_blockers list değil")
    try:
        expected = reduce_risk_mode(data["active_blockers"])  # bilinmeyen blocker → ValueError
    except ValueError as e:
        raise RiskStateCorruptError(f"active_blockers tanınmayan blocker içeriyor: {e}")
    if data["effective_mode"] != expected:
        raise RiskStateCorruptError(
            f"effective_mode reducer ile tutarsız: saklı={data['effective_mode']} beklenen={expected}")
