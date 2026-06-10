"""data/orderbook_snapshot.py — Atomic orderbook snapshot (P0 data-integrity).

Entry karar yoluna TEK obje verilir: bid+ask AYNI snapshot'tan (Frankenstein yasak),
crossed/dust/stale → invalid. Karar mantığını (fair/edge/threshold) DEĞİŞTİRMEZ;
yalnızca fiyat snapshot kalitesini garantiler.
"""
from dataclasses import dataclass
import time as _time


@dataclass
class OrderbookSnapshot:
    bid: float | None
    ask: float | None
    bid_size: float | None
    ask_size: float | None
    source: str            # 'ws' | 'rest_book'
    ts: float              # epoch saniye (atomik snapshot zamanı)

    @property
    def is_crossed(self) -> bool:
        """bid >= ask → crossed (stale/kısmi update artefaktı)."""
        return (self.bid is not None and self.ask is not None
                and self.bid >= self.ask)

    @property
    def age_s(self) -> float:
        return _time.time() - self.ts

    def valid(self, min_notional: float = 0.0, max_age_s: float | None = None) -> bool:
        """Snapshot entry'ye girebilir mi? bid+ask dolu, pozitif, non-crossed,
        dust-üstü (min_notional), taze (max_age_s)."""
        if self.bid is None or self.ask is None:
            return False
        if self.bid <= 0 or self.ask <= 0:
            return False
        if self.is_crossed:
            return False
        if min_notional > 0:
            # her iki taraf da executable notional eşiğini geçmeli (dust top-of-book engeli)
            if (self.bid_size or 0) * self.bid < min_notional:
                return False
            if (self.ask_size or 0) * self.ask < min_notional:
                return False
        if max_age_s is not None and self.age_s > max_age_s:
            return False
        return True
