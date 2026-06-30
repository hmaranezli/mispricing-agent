"""
analysis.forensic.gateg5_model — pure Decimal diagnostic model for G.5 telemetry.

Reuses the Decimal-safe GBM digital model from analysis/golden_sample_economics.py
(same d2 / normal-CDF / edge formula) so telemetry edge is computed identically to
the validated Golden Sample pipeline. Pure: no network, no DB, no clock, no float
money math. This is a DIAGNOSTIC model, not a settlement oracle.

NOTE (data fidelity): Polymarket up/down markets settle on the Chainlink BTC/USD
data stream; the reference/strike fed here are a Hyperliquid DIAGNOSTIC BASIS, not
the settlement oracle. Edge produced here is HL-basis diagnostic, not alpha.
"""

from __future__ import annotations

from decimal import Decimal

from analysis import golden_sample_economics as gse

# 365 * 24 * 3600 — matches gse._MS_PER_YEAR (/1000); diagnostic annualization.
SECONDS_PER_YEAR = Decimal(365 * 24 * 60 * 60)


class ModelInputError(Exception):
    """Non-finite / non-positive model input (fail closed; never silent)."""


def _d(value, name: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ModelInputError(f"{name} not numeric: {value!r}") from exc
    if not d.is_finite():
        raise ModelInputError(f"{name} non-finite: {value!r}")
    return d


def fair_yes_gbm(reference, strike, sigma_annual, tte_years,
                 drift_annual=Decimal(0)) -> Decimal:
    """P(underlying_end >= strike) under no-drift(default) GBM, Decimal-safe.

    Same formula as golden_sample_economics:
      d2 = (ln(reference/strike) + (drift - sigma^2/2)*tte) / (sigma*sqrt(tte))
      p_up = Normal_CDF(d2)
    """
    r = _d(reference, "reference")
    k = _d(strike, "strike")
    sig = _d(sigma_annual, "sigma_annual")
    tte = _d(tte_years, "tte_years")
    drift = _d(drift_annual, "drift_annual")
    if r <= 0 or k <= 0:
        raise ModelInputError("nonpositive reference/strike")
    if sig <= 0:
        raise ModelInputError("nonpositive sigma")
    if tte <= 0:
        raise ModelInputError("nonpositive tte")
    d2 = ((r / k).ln() + (drift - sig * sig / Decimal(2)) * tte) / (sig * tte.sqrt())
    return gse._normal_cdf(d2)


def no_side_entry_edge(fair_yes, exec_ask_vwap, *, fee=Decimal(0),
                       slippage=Decimal(0), margin=Decimal(0)) -> Decimal:
    """Diagnostic NO-leg edge = (1 - fair_yes) - exec_ask_vwap - fee - slippage - margin.

    Mirrors golden_sample_economics no_edge = (1 - p_up) - no_vwap - fee - slippage - margin.
    """
    return ((Decimal(1) - _d(fair_yes, "fair_yes"))
            - _d(exec_ask_vwap, "exec_ask_vwap")
            - _d(fee, "fee") - _d(slippage, "slippage") - _d(margin, "margin"))
