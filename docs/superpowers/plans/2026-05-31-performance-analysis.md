# Performance Analysis Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `analysis/performance.py` — tek çalıştırmada dry-run strateji performansını terminal'e formatlanmış tablo olarak basar.

**Architecture:** Bağımsız Python script. `db.logger.get_connection()` ile SQLite bağlantısı açar, async sorgular çalıştırır, stdout'a plain-text tablolar basar. Hiç yeni dependency yok.

**Tech Stack:** Python 3.12, aiosqlite (zaten mevcut), argparse, asyncio

---

## Dosya Haritası

| Dosya | İşlem | Açıklama |
|-------|--------|----------|
| `analysis/__init__.py` | Oluştur | Boş — module marker |
| `analysis/performance.py` | Oluştur | Tüm script: query + format + main |

---

### Task 1: `analysis/` dizini ve `performance.py`

**Files:**
- Create: `analysis/__init__.py`
- Create: `analysis/performance.py`

- [ ] **Step 1: `analysis/__init__.py` oluştur (boş)**

```bash
mkdir -p analysis && touch analysis/__init__.py
```

- [ ] **Step 2: `analysis/performance.py` yaz**

```python
#!/usr/bin/env python3
"""analysis/performance.py — Dry-run strateji performans analizi."""
import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.logger import get_connection

SEP = "=" * 58
DIV = "-" * 58


async def _overview(conn, where: str, params: list) -> dict:
    async with conn.execute(f"""
        SELECT
            COUNT(*) total,
            SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) wins,
            SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) losses,
            SUM(CASE WHEN realized_pnl IS NULL THEN 1 ELSE 0 END) nulls,
            ROUND(SUM(COALESCE(realized_pnl, 0)), 2) net_pnl,
            ROUND(AVG(CASE WHEN realized_pnl IS NOT NULL THEN realized_pnl END), 2) avg_pnl
        FROM positions WHERE status='closed' {where}
    """, params) as c:
        r = await c.fetchone()
    total, wins, losses, nulls, net_pnl, avg_pnl = r
    return {
        "total": total or 0,
        "wins": wins or 0,
        "losses": losses or 0,
        "nulls": nulls or 0,
        "net_pnl": net_pnl or 0.0,
        "avg_pnl": avg_pnl or 0.0,
    }


async def _by_exit_reason(conn, where: str, params: list) -> list:
    async with conn.execute(f"""
        SELECT exit_reason, COUNT(*),
               ROUND(AVG(realized_pnl), 2),
               ROUND(SUM(COALESCE(realized_pnl, 0)), 2)
        FROM positions WHERE status='closed' {where}
        GROUP BY exit_reason ORDER BY COUNT(*) DESC
    """, params) as c:
        return await c.fetchall()


async def _by_asset(conn, where: str, params: list) -> list:
    async with conn.execute(f"""
        SELECT asset, COUNT(*),
               SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) wins,
               ROUND(SUM(COALESCE(realized_pnl, 0)), 2) net
        FROM positions WHERE status='closed' {where}
        GROUP BY asset ORDER BY net DESC
    """, params) as c:
        return await c.fetchall()


async def _veto_stats(conn) -> tuple[int, list]:
    async with conn.execute("SELECT COUNT(*) FROM candidates") as c:
        total = (await c.fetchone())[0]
    async with conn.execute("""
        SELECT passed, veto_layer, COUNT(*)
        FROM candidates GROUP BY passed, veto_layer
        ORDER BY COUNT(*) DESC
    """) as c:
        rows = await c.fetchall()
    return total, rows


async def _top_trades(conn, where: str, params: list, n: int = 3) -> tuple[list, list]:
    base = f"SELECT asset, action, realized_pnl, exit_reason, pm_entry_price, pm_exit_price FROM positions WHERE status='closed' AND realized_pnl IS NOT NULL {where}"
    async with conn.execute(f"{base} ORDER BY realized_pnl DESC LIMIT {n}", params) as c:
        winners = await c.fetchall()
    async with conn.execute(f"{base} ORDER BY realized_pnl ASC  LIMIT {n}", params) as c:
        losers = await c.fetchall()
    return winners, losers


def _pct(num: int, denom: int) -> str:
    return f"{num / denom * 100:.1f}%" if denom else "N/A"


def _trade_line(r) -> str:
    asset, action, pnl, reason, entry, exit_p = r
    pct = (exit_p - entry) / entry * 100 if entry and exit_p else 0.0
    return f"  {asset} {action:<3} | {reason:<22} | ${pnl:>+7.2f}  ({pct:>+6.1f}%)"


async def run(days: int | None = None, asset: str | None = None) -> None:
    conn = await get_connection()

    where_parts = []
    params: list = []
    if days:
        where_parts.append("ts_close >= datetime('now', ?, 'utc')")
        params.append(f"-{days} days")
    if asset:
        where_parts.append("asset = ?")
        params.append(asset.upper())
    where = ("AND " + " AND ".join(where_parts)) if where_parts else ""

    ov = await _overview(conn, where, params)
    exit_rows = await _by_exit_reason(conn, where, params)
    asset_rows = await _by_asset(conn, where, params)
    cand_total, veto_rows = await _veto_stats(conn)
    winners, losers = await _top_trades(conn, where, params)

    total = ov["total"]
    label = f"son {days} gün" if days else "tüm zaman"
    if asset:
        label += f" | {asset.upper()}"

    # 1. Genel bakış
    print(f"\n{SEP}")
    print(f"  GENEL BAKIŞ ({label})")
    print(SEP)
    print(f"  Toplam trade  : {total}")
    print(f"  Kazanan       : {ov['wins']}  (Win rate: {_pct(ov['wins'], total)})")
    print(f"  Kaybeden      : {ov['losses']}")
    print(f"  Belirsiz      : {ov['nulls']}  (market_expired)")
    print(f"  Net P&L       : ${ov['net_pnl']:+.2f}")
    print(f"  Ortalama P&L  : ${ov['avg_pnl']:+.2f} / trade")

    # 2. Exit reason
    print(f"\n{DIV}")
    print(f"  {'EXIT REASON':<22} {'Adet':>5} {'Oran':>6} {'Ort P&L':>9} {'Toplam':>10}")
    print(DIV)
    for reason, cnt, avg, tot in exit_rows:
        avg_s = f"${avg:+.2f}" if avg is not None else "   N/A"
        tot_s = f"${tot:+.2f}" if tot is not None else "     N/A"
        print(f"  {reason:<22} {cnt:>5} {_pct(cnt, total):>6} {avg_s:>9} {tot_s:>10}")

    # 3. Asset
    print(f"\n{DIV}")
    print(f"  {'ASSET':<6} {'Trade':>6} {'Kazan':>6} {'Win%':>6} {'Net P&L':>10}")
    print(DIV)
    for ast, cnt, wins_a, net in asset_rows:
        print(f"  {ast:<6} {cnt:>6} {wins_a or 0:>6} {_pct(wins_a or 0, cnt):>6} ${net:>+9.2f}")

    # 4. Konsey
    print(f"\n{DIV}")
    print(f"  KONSEY VETO (toplam {cand_total:,} aday)")
    print(DIV)
    for passed, layer, cnt in veto_rows:
        label_v = "PASS" if passed else f"VETO({layer})"
        print(f"  {label_v:<22} {cnt:>6,}  ({_pct(cnt, cand_total)})")

    # 5. Top trades
    print(f"\n{DIV}")
    print("  TOP 3 KAZANAN")
    print(DIV)
    for r in winners:
        print(_trade_line(r))

    print(f"\n  TOP 3 KAYBEDEN")
    print(DIV)
    for r in losers:
        print(_trade_line(r))

    print(f"\n{SEP}\n")
    await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run performans analizi")
    parser.add_argument("--days", type=int, default=None,
                        help="Son N günün verisi (default: tüm zaman)")
    parser.add_argument("--asset", type=str, default=None,
                        help="Asset filtresi: BTC ETH SOL XRP")
    args = parser.parse_args()
    asyncio.run(run(days=args.days, asset=args.asset))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Çalıştır ve çıktıyı doğrula**

```bash
source venv/bin/activate && python analysis/performance.py
```

Beklenen: Tüm bölümler (GENEL BAKIŞ, EXIT REASON, ASSET, KONSEY, TOP 3) hatasız basılır.

```bash
python analysis/performance.py --days 1
python analysis/performance.py --asset BTC
```

Beklenen: Filtrelenmiş çıktı, hata yok.

- [ ] **Step 4: Commit**

```bash
git add analysis/__init__.py analysis/performance.py
git commit -m "feat(analysis): performance analiz scripti — win rate, P&L, veto dağılımı"
```

---

## Self-Review Notu

- Spec'teki tüm bölümler karşılandı: genel bakış, exit reason, asset, konsey veto, top trades ✓
- `--days` ve `--asset` parametreleri eklendi ✓
- Yeni dependency yok ✓
- `db.logger.get_connection()` ile mevcut DB altyapısı kullanıldı ✓
- Sıfır placeholder ✓
