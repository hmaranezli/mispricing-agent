"""data/ws_prices.py — Polymarket CLOB WebSocket fiyat önbelleği.

Endpoint  : wss://ws-subscriptions-clob.polymarket.com/ws/market
Döküman   : https://docs.polymarket.com  (AsyncAPI Market Channel)
Kullanım  : asyncio.create_task(ws_prices.run(initial_token_ids=[...]))
"""
import asyncio
import json
import time
import websockets

WS_URL             = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
PING_INTERVAL      = 8    # saniye — sunucunun 10s limitinin 2s öncesi
RECONNECT_DELAY    = 5    # bağlantı kopunca bekle
STALE_SECS         = 15   # bu kadar eski cache girdisi stale sayılır
_SHORT_LIVED_SECS  = 15   # bu kadar kısa bağlantı = "short-lived" sayılır
_CIRCUIT_BREAKER_N = 8    # kaç ard arda kısa bağlantıda Telegram uyarısı

# ── Modül düzeyi durum ────────────────────────────────────────────────────────
_cache:    dict[str, dict]       = {}   # token_id → {best_bid, best_ask, spread, ts}
_subscribed: set[str]            = set()
_pending:    set[str]            = set()
_pending_unsub: set[str]         = set()   # unsubscribe kuyruğu
_ws                              = None
_resolved_queue: asyncio.Queue | None = None
_price_event: asyncio.Event | None = None
_reconnect_count: int            = 0
_short_lived_count: int          = 0   # ard arda kısa bağlantı sayısı


# ── Public API ────────────────────────────────────────────────────────────────

def get_ask(token_id: str) -> float | None:
    """Cache'deki best_ask. None → kayıt yok veya stale."""
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS and entry["best_ask"] > 0:
        return entry["best_ask"]
    return None


def get_bid(token_id: str) -> float | None:
    """Cache'deki best_bid. None → kayıt yok veya stale."""
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS and entry["best_bid"] > 0:
        return entry["best_bid"]
    return None


def get_spread(token_id: str) -> float | None:
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS:
        return entry.get("spread")
    return None


def subscribe(token_ids: list[str]) -> None:
    """Token ID'leri subscribe listesine ekle. WS aktifse 2s içinde gönderilir."""
    _pending.update(t for t in token_ids if t and t not in _subscribed)


def unsubscribe(token_ids: list[str]) -> None:
    """Token ID'lerini abonelikten çıkar. WS aktifse 2s içinde unsubscribe gönderilir."""
    for tid in token_ids:
        if tid:
            _subscribed.discard(tid)
            _pending.discard(tid)
            _pending_unsub.add(tid)


def get_price_event() -> asyncio.Event:
    """WS fiyat güncellemelerini dinleyen global asyncio.Event (lazy init)."""
    global _price_event
    if _price_event is None:
        _price_event = asyncio.Event()
    return _price_event


async def run(initial_token_ids: list[str] | None = None) -> None:
    """Ana WS döngüsü. asyncio.create_task ile çalıştırılır."""
    global _resolved_queue, _short_lived_count
    if _resolved_queue is None:
        _resolved_queue = asyncio.Queue()
    if initial_token_ids:
        subscribe(initial_token_ids)
    while True:
        # Token yoksa bekleme — no-sub kill önlemi
        while not _pending and not _subscribed:
            await asyncio.sleep(1)
        had_subs = bool(_subscribed or _pending)
        t_start = time.time()
        try:
            await _connect_and_run()
            _short_lived_count = 0  # temiz çıkış → sayacı sıfırla
        except Exception as e:
            lifetime = time.time() - t_start
            etype    = type(e).__name__
            print(f"[ws] Bağlantı koptu ({lifetime:.1f}s): {etype}: {e} — {RECONNECT_DELAY}s sonra yeniden deneniyor")
            if lifetime < _SHORT_LIVED_SECS and had_subs:
                _short_lived_count += 1
                if _short_lived_count >= _CIRCUIT_BREAKER_N:
                    _warn_ws_circuit_breaker(_short_lived_count)
                    _short_lived_count = 0
            else:
                _short_lived_count = 0
        await asyncio.sleep(RECONNECT_DELAY)


def _warn_ws_circuit_breaker(count: int) -> None:
    """Ard arda kısa bağlantılar → Telegram uyarısı."""
    msg = f"[ws] UYARI: WS {count} kez ard arda kısa bağlantı (<{_SHORT_LIVED_SECS}s) — bot REST fallback ile çalışıyor"
    print(msg)
    try:
        from monitor.notifier import send_telegram
        send_telegram(msg)
    except Exception:
        pass


# ── İç fonksiyonlar ───────────────────────────────────────────────────────────

def _update_cache(token_id: str, best_bid: float | None, best_ask: float | None,
                  spread: float | None = None) -> None:
    if not token_id:
        return
    # Nothing meaningful to store — don't create or touch the entry
    if best_bid is None and best_ask is None and spread is None:
        return
    entry = _cache.setdefault(token_id,
                               {"best_bid": 0.0, "best_ask": 0.0, "spread": None, "ts": 0})
    if best_bid is not None and best_bid > 0:
        entry["best_bid"] = best_bid
    if best_ask is not None and best_ask > 0:
        entry["best_ask"] = best_ask
    if spread is not None:
        entry["spread"] = spread
    entry["ts"] = time.time()
    if _price_event is not None:
        _price_event.set()


def _handle_book(event: dict) -> None:
    token_id = event.get("asset_id")
    bids = event.get("bids", [])
    asks = event.get("asks", [])
    best_bid = float(max(bids, key=lambda x: float(x["price"]))["price"]) if bids else None
    best_ask = float(min(asks, key=lambda x: float(x["price"]))["price"]) if asks else None
    _update_cache(token_id, best_bid, best_ask)


def _handle_price_change(event: dict) -> None:
    for change in event.get("price_changes", []):
        token_id = change.get("asset_id")
        raw_bid  = change.get("best_bid")
        raw_ask  = change.get("best_ask")
        _update_cache(
            token_id,
            float(raw_bid) if raw_bid else None,
            float(raw_ask) if raw_ask else None,
        )


def _handle_best_bid_ask(event: dict) -> None:
    token_id = event.get("asset_id")
    raw_bid  = event.get("best_bid")
    raw_ask  = event.get("best_ask")
    raw_spr  = event.get("spread")
    _update_cache(
        token_id,
        float(raw_bid) if raw_bid else None,
        float(raw_ask) if raw_ask else None,
        float(raw_spr) if raw_spr else None,
    )


def _handle_market_resolved(event: dict) -> None:
    if _resolved_queue is not None:
        _resolved_queue.put_nowait(event)


async def _flush_pending(ws, *, initial_connect: bool = True) -> None:
    """_pending tokenlarını subscribe et + _pending_unsub tokenlarını unsubscribe et.

    initial_connect=True  → ilk bağlantı formatı: {"assets_ids": [...], "type": "market"}
    initial_connect=False → update formatı: {"operation": "subscribe", "assets_ids": [...]}
    """
    # Önce unsubscribe mesajlarını gönder
    if _pending_unsub:
        unsub_batch = list(_pending_unsub)
        _pending_unsub.clear()
        for tid in unsub_batch:
            _subscribed.discard(tid)
        msg = json.dumps({"operation": "unsubscribe", "assets_ids": unsub_batch})
        print(f"[ws] Unsubscribe: {len(unsub_batch)} token")
        await ws.send(msg)
        # Explicit clean close: tüm abonelikler gittiyse bağlantıyı kapat
        if not _subscribed and not _pending:
            print("[ws] no subscriptions remaining — clean close")
            await ws.close(code=1000, reason="no_subscriptions")
            return

    if not _pending:
        return
    batch = list(_pending)
    _pending.clear()          # atomic clear before await — no TOCTOU
    if initial_connect:
        msg = json.dumps({
            "assets_ids":             batch,
            "type":                   "market",
            "custom_feature_enabled": True,
        })
        print(f"[ws] Subscribe (initial): {len(batch)} token, ilk: {batch[:3]}")
    else:
        msg = json.dumps({
            "operation":              "subscribe",
            "assets_ids":             batch,
            "custom_feature_enabled": True,
        })
        print(f"[ws] Subscribe (update): {len(batch)} token, ilk: {batch[:3]}")
    await ws.send(msg)
    _subscribed.update(batch)


async def _connect_and_run() -> None:
    global _ws, _reconnect_count
    _reconnect_count += 1
    if _reconnect_count > 1:
        print(f"[ws] Yeniden bağlanıyor (#{_reconnect_count})...")
    if not _pending and not _subscribed:
        print(f"[ws] WARNING: token listesi boş — sunucu idle bağlantıyı kesebilir")
    # NOT: Lib-level keepalive yok — Polymarket WS lib frame ping desteklemiyor.
    # Uygulama seviyesi _ping_loop ("PING"/"PONG" text) kullanılır.
    async with websockets.connect(WS_URL) as ws:
        _ws = ws
        print(f"[ws] Polymarket CLOB WebSocket bağlandı (#{_reconnect_count})")
        # Reconnect sonrası tüm subscribed tokenları yeniden abone et
        if _subscribed:
            _pending.update(_subscribed)
            _subscribed.clear()
        await _flush_pending(ws, initial_connect=True)
        ping_task  = asyncio.create_task(_ping_loop(ws))
        flush_task = asyncio.create_task(_pending_flush_loop(ws))
        msg_count     = 0
        pc_count      = 0
        bk_count      = 0
        _last_stats_ts = time.time()
        try:
            async for raw in ws:
                if raw == "PONG":
                    continue
                msg_count += 1
                try:
                    event = json.loads(raw)
                    etype = event.get("event_type")
                    if msg_count <= 3:
                        print(f"[ws] İlk mesaj #{msg_count}: event_type={etype!r}")
                    if   etype == "book":
                        bk_count += 1
                        _handle_book(event)
                    elif etype == "price_change":
                        pc_count += 1
                        _handle_price_change(event)
                    elif etype == "best_bid_ask":    _handle_best_bid_ask(event)
                    elif etype == "market_resolved": _handle_market_resolved(event)
                    _now = time.time()
                    if msg_count % 10000 == 0 or (_now - _last_stats_ts) >= 60:
                        print(f"[ws] Sayaç #{_reconnect_count}: {msg_count} mesaj "
                              f"({pc_count} price_change, {bk_count} book) "
                              f"subscribed={len(_subscribed)} pending={len(_pending)}")
                        _last_stats_ts = _now
                except (json.JSONDecodeError, KeyError, ValueError, AttributeError, TypeError):
                    pass
        finally:
            ping_task.cancel()
            flush_task.cancel()
            _ws = None


async def _ping_loop(ws) -> None:
    # İlk PING: subscribe sonrası hemen (1s) — sunucu 10s içinde PING bekliyor
    await asyncio.sleep(1)
    try:
        await ws.send("PING")
    except Exception:
        return
    # Sonra her 8s'de bir (10s limitin 2s öncesi)
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            await ws.send("PING")
        except Exception:
            break


async def _pending_flush_loop(ws) -> None:
    while True:
        await asyncio.sleep(2)
        try:
            await _flush_pending(ws, initial_connect=False)
        except Exception:
            break
