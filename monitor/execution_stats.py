"""monitor/execution_stats.py — E12b: process-runtime execution sayaçları için tek konteyner.

E10/E11 boyunca main_loop'a yayılan üç process-runtime sayacını (`_SESSION_TRADE_COUNT` /
`_NO_FILL_STREAK` / `_SESSION_SUBMIT_COUNT`) ve reset/increment helper'larını tek bir SAF, in-memory
nesnede merkezileştirir — testler tek izolasyon yüzeyi alır. Bu slice yalnız abstraction'ı sağlar;
DAVRANIŞ DEĞİŞMEZ (main_loop wiring AYRI bir slice). Persistence/DB/restore_state YOK; restart-safe DEĞİL.

Saf: DB/config/main_loop/network/clock importu YOK. Sayaçlar public API üzerinden asla negatife düşmez.
"""


class ExecutionStats:
    """Process-runtime execution sayaçları (trade_count, no_fill_streak, submit_count).

    trade_count: bu seansta gerçekten açılan işlem (E10c).
    no_fill_streak: ardışık no-fill/no-open (E11b).
    submit_count: bu seansta yapılan gerçek execute()/submit (E11e).
    """

    def __init__(self, trade_count: int = 0, no_fill_streak: int = 0, submit_count: int = 0):
        if trade_count < 0:
            raise ValueError(f"trade_count negatif olamaz: {trade_count}")
        if no_fill_streak < 0:
            raise ValueError(f"no_fill_streak negatif olamaz: {no_fill_streak}")
        if submit_count < 0:
            raise ValueError(f"submit_count negatif olamaz: {submit_count}")
        self._trade_count = int(trade_count)
        self._no_fill_streak = int(no_fill_streak)
        self._submit_count = int(submit_count)

    @property
    def trade_count(self) -> int:
        return self._trade_count

    @property
    def no_fill_streak(self) -> int:
        return self._no_fill_streak

    @property
    def submit_count(self) -> int:
        return self._submit_count

    def increment_trade_count(self) -> None:
        """E10c — gerçek açılışta seans işlem sayacını +1."""
        self._trade_count += 1

    def increment_no_fill_streak(self) -> None:
        """E11b — no-fill/no-open çıktısında ardışık no-fill sayacını +1."""
        self._no_fill_streak += 1

    def increment_submit_count(self) -> None:
        """E11e — her gerçek execute() çağrısında submit sayacını +1."""
        self._submit_count += 1

    def reset_trade_count(self) -> None:
        self._trade_count = 0

    def reset_no_fill_streak(self) -> None:
        """E11b — gerçek açılışta ardışık no-fill sayacını 0'a çeker."""
        self._no_fill_streak = 0

    def reset_submit_count(self) -> None:
        self._submit_count = 0

    def reset_all(self) -> None:
        """Üç sayacı da 0'a çeker (process start / test izolasyonu)."""
        self._trade_count = 0
        self._no_fill_streak = 0
        self._submit_count = 0

    def snapshot(self) -> dict:
        """Sayaçların plain int kopyasını döndürür. NON-MUTATING: dönen dict düzenlenirse nesne değişmez."""
        return {
            "trade_count": self._trade_count,
            "no_fill_streak": self._no_fill_streak,
            "submit_count": self._submit_count,
        }
