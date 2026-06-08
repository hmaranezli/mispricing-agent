"""scripts/report_20trades.py — Epoch 3 (kalibrasyon sonrası) trade raporu.

Kullanım:
  python scripts/report_20trades.py           # Epoch 3 ilk 20 trade
  python scripts/report_20trades.py 30        # Epoch 3 ilk 30 trade
  python scripts/report_20trades.py --all     # tüm zamanlar (Epoch 3 filtresi yok)
  python scripts/report_20trades.py --live    # dry_run=0 filtresi
"""
import sqlite3
import sys
import statistics
from pathlib import Path
from collections import Counter

DB_PATH          = Path("logs/mispricing.db")
EPOCH3_START_SEQ = 1336   # 2026-06-08 07:27 UTC — kalibrasyon fix sonrası ilk temiz trade
N                = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
LIVE             = "--live" in sys.argv
EPOCH3_ONLY      = "--all" not in sys.argv   # varsayılan: Epoch 3


def pct(val):
    return f"{val*100:+.1f}%" if val is not None else "—"

def fmt(val, decimals=4):
    return f"{val:.{decimals}f}" if val is not None else "—"


con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

where_dry   = "AND dry_run = 0" if LIVE else ""
where_epoch = f"AND seq_no >= {EPOCH3_START_SEQ}" if EPOCH3_ONLY else ""
epoch_label = f"Epoch 3 (seq≥{EPOCH3_START_SEQ})" if EPOCH3_ONLY else "Tüm Zamanlar"

rows = con.execute(f"""
    SELECT *
    FROM positions
    WHERE status = 'closed'
    {where_dry}
    {where_epoch}
    ORDER BY ts_close DESC
    LIMIT {N}
""").fetchall()
con.close()

rows = list(reversed(rows))   # kronolojik sıra

if not rows:
    print(f"Henüz kapalı pozisyon yok (LIVE={LIVE}).")
    sys.exit(0)

n = len(rows)

# ── Temel metrikler ────────────────────────────────────────────────────────────
wins    = [r for r in rows if (r["realized_pnl"] or 0) > 0]
losses  = [r for r in rows if (r["realized_pnl"] or 0) <= 0]
wr      = len(wins) / n * 100
net_pnl = sum(r["realized_pnl"] or 0 for r in rows)

# ── MAE/MFE ───────────────────────────────────────────────────────────────────
mae_vals = [r["mae_pct"] for r in rows if r["mae_pct"] is not None]
mfe_vals = [r["mfe_pct"] for r in rows if r["mfe_pct"] is not None]

avg_mae   = statistics.mean(mae_vals)  if mae_vals else None
worst_mae = min(mae_vals)              if mae_vals else None
avg_mfe   = statistics.mean(mfe_vals)  if mfe_vals else None
best_mfe  = max(mfe_vals)             if mfe_vals else None

# ── mae_data_quality dağılımı ──────────────────────────────────────────────────
quality_dist = Counter(r["mae_data_quality"] or "null" for r in rows)

# ── price_source dağılımı ─────────────────────────────────────────────────────
source_dist = Counter(r["price_source"] or "null" for r in rows)

# ── exit_reason dağılımı ──────────────────────────────────────────────────────
reason_dist = Counter(r["exit_reason"] or "null" for r in rows)

# ── Stop trade detayı ─────────────────────────────────────────────────────────
stops = [r for r in rows if r["exit_reason"] == "stop_loss_hit"]

# ETH-NO quarantine kontrolü
eth_no = [r for r in rows if r["asset"] == "ETH" and r["action"] == "NO"]

# ── Rapor ─────────────────────────────────────────────────────────────────────
sep = "─" * 60

print(f"\n{'═'*60}")
print(f"  İLK {n} TRADE RAPORU — {epoch_label}{'  [LIVE]' if LIVE else ''}")
print(f"{'═'*60}")

print(f"\n{'GENEL PERFORMANS':}")
print(f"  Toplam trade : {n}")
print(f"  Kazanma oranı: {wr:.1f}%  ({len(wins)}W / {len(losses)}L)")
print(f"  Net P&L      : {net_pnl:+.4f} USDC")
if wins:
    avg_win = statistics.mean(r["realized_pnl"] for r in wins)
    print(f"  Avg win      : {avg_win:+.4f} USDC")
if losses:
    avg_loss = statistics.mean(r["realized_pnl"] for r in losses)
    print(f"  Avg loss     : {avg_loss:+.4f} USDC")

print(f"\n{sep}")
print(f"MAE / MFE")
print(f"{sep}")
print(f"  avg  MAE     : {pct(avg_mae)}")
print(f"  worst MAE    : {pct(worst_mae)}")
print(f"  avg  MFE     : {pct(avg_mfe)}")
print(f"  best MFE     : {pct(best_mfe)}")

print(f"\n{sep}")
print(f"MAE DATA QUALITY")
print(f"{sep}")
for k, v in quality_dist.most_common():
    print(f"  {k:<20} {v:>3}  ({v/n*100:.0f}%)")

print(f"\n{sep}")
print(f"PRICE SOURCE")
print(f"{sep}")
for k, v in source_dist.most_common():
    print(f"  {k:<30} {v:>3}  ({v/n*100:.0f}%)")

print(f"\n{sep}")
print(f"EXIT REASON")
print(f"{sep}")
for k, v in reason_dist.most_common():
    print(f"  {k:<25} {v:>3}  ({v/n*100:.0f}%)")

print(f"\n{sep}")
print(f"ETH-NO QUARANTINE KONTROLü")
print(f"{sep}")
print(f"  ETH-NO trade sayısı: {len(eth_no)}  (hedef: 0)")
if eth_no:
    for r in eth_no:
        print(f"  !! {r['slug']}  pnl={r['realized_pnl']:+.4f}")

if stops:
    print(f"\n{sep}")
    print(f"STOP TRADE ANALİZİ  ({len(stops)} stop)")
    print(f"{sep}")

    sl_trig   = [r["sl_trigger_pct"] for r in stops if r["sl_trigger_pct"] is not None]
    sl_fill   = [r["sl_fill_pct"]    for r in stops if r["sl_fill_pct"]    is not None]
    mae_sl    = [r["mae_pct"]        for r in stops if r["mae_pct"]        is not None]
    gap       = [r["trigger_fill_gap_pct"] for r in stops if r["trigger_fill_gap_pct"] is not None]
    ttf       = [r["trigger_to_fill_secs"] for r in stops if r["trigger_to_fill_secs"] is not None]
    attempts  = [r["sell_attempt_count"]   for r in stops if r["sell_attempt_count"]   is not None]
    unmatched = [r["sell_unmatched_count"] for r in stops if r["sell_unmatched_count"] is not None]

    if sl_trig:
        print(f"  avg sl_trigger_pct  : {pct(statistics.mean(sl_trig))}  (hedef ≈ -25%)")
        print(f"  worst sl_trigger_pct: {pct(min(sl_trig))}")
    if sl_fill:
        print(f"  avg sl_fill_pct     : {pct(statistics.mean(sl_fill))}")
    if mae_sl:
        print(f"  avg MAE@stop        : {pct(statistics.mean(mae_sl))}")
    if gap:
        print(f"  avg trigger→fill gap: {pct(statistics.mean(gap))}  (negatif=fill kötüleşti)")
        n_bad_gap = sum(1 for g in gap if g <= -0.10)
        print(f"  count gap ≤ -10pp   : {n_bad_gap}/{len(gap)}{'  ← YAPISI SORUN?' if n_bad_gap > 1 else ''}")

    # ── Execution risk üç boyutu ─────────────────────────────────────────────
    print(f"\n  --- Execution Risk ---")
    print(f"  [Price Risk]    trigger→fill gap")
    if gap:
        print(f"    avg gap       : {pct(statistics.mean(gap))}")
        print(f"    max gap       : {pct(min(gap))}")
        print(f"    count >-10pp  : {sum(1 for g in gap if g <= -0.10)}/{len(gap)}")

    print(f"  [Liquidity Risk] sell_attempt / fak_no_match")
    if attempts:
        print(f"    avg attempts  : {statistics.mean(attempts):.1f}")
        print(f"    max attempts  : {max(attempts)}")
        print(f"    count >1      : {sum(1 for a in attempts if a > 1)}/{len(attempts)}")
    if unmatched:
        print(f"    avg no_match  : {statistics.mean(unmatched):.1f}")
        print(f"    max no_match  : {max(unmatched)}")

    print(f"  [Time Risk]     trigger_to_fill_secs")
    if ttf:
        print(f"    avg TTF       : {statistics.mean(ttf):.1f}s")
        print(f"    max TTF       : {max(ttf):.1f}s")
        n_slow = sum(1 for t in ttf if t > 3.0)
        print(f"    count >3s     : {n_slow}/{len(ttf)}{'  ← AIR POCKET?' if n_slow > 0 else ''}")

    # stop_quality dağılımı
    stop_quality = Counter(r["mae_data_quality"] or "null" for r in stops)
    print(f"\n  Stop quality dağılımı:")
    for k, v in stop_quality.most_common():
        flag = "  ← ESTIMATED_STOP!" if k == "estimated" else ""
        print(f"    {k:<20} {v:>2}{flag}")

    # sl_trigger uyumu: mae_pct yakın mı?
    aligned = [(r["mae_pct"], r["sl_trigger_pct"]) for r in stops
               if r["mae_pct"] is not None and r["sl_trigger_pct"] is not None]
    if aligned:
        deltas = [abs(m - s) for m, s in aligned]
        print(f"\n  MAE↔sl_trigger delta (uyum): avg={statistics.mean(deltas)*100:.1f}pp")
        tight = sum(1 for d in deltas if d < 0.03)
        print(f"  Sıkı uyum (<3pp): {tight}/{len(deltas)}")

    print(f"\n  Per-stop detay:")
    print(f"  {'slug':<30} {'mae':>7} {'sl_trig':>8} {'sl_fill':>8} {'gap':>7} {'ttf':>5} {'att':>4} {'nomatch':>7}  quality")
    print(f"  {'-'*95}")
    for r in stops:
        att_s  = str(r["sell_attempt_count"]   or "—")
        nom_s  = str(r["sell_unmatched_count"] or "—")
        flags  = ""
        if r["trigger_to_fill_secs"] and r["trigger_to_fill_secs"] > 3:
            flags += " ⚠TTF"
        if r["sell_attempt_count"] and r["sell_attempt_count"] > 1:
            flags += " ⚠ATT"
        print(f"  {(r['slug'] or '')[:30]:<30} "
              f"{pct(r['mae_pct']):>7} "
              f"{pct(r['sl_trigger_pct']):>8} "
              f"{pct(r['sl_fill_pct']):>8} "
              f"{pct(r['trigger_fill_gap_pct']):>7} "
              f"{fmt(r['trigger_to_fill_secs'],1) if r['trigger_to_fill_secs'] else '—':>5}s "
              f"{att_s:>4} "
              f"{nom_s:>7}  "
              f"{r['mae_data_quality'] or '—'}{flags}")

print(f"\n{'═'*60}\n")
