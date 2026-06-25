"""tests/test_reference_collector_isolation.py — Tier-0 collector is fully isolated (TDD).

The collector and fetchers must NOT import or invoke trading/runtime surfaces: main_loop, council.scout,
execution/*, position/*, monitor/Telegram, or S1 storage. Proven by static import inspection of the two
new module source files (no forbidden import lines).

First RED: modules do not exist → import for __file__ fails.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data.public_spot_fetchers as fetchers
import data.reference_collector as collector

_FORBIDDEN = (
    "main_loop", "council.scout", "council import scout", "execution", "position",
    "monitor", "telegram", "phase6_1_s1_storage", "s1_storage", "hl_candles",
)


def _source(mod):
    with open(mod.__file__, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("mod", [fetchers, collector])
def test_no_forbidden_imports_in_source(mod):
    src = _source(mod)
    # only inspect import lines (avoid matching words inside comments/strings incidentally)
    import_lines = [ln for ln in src.splitlines()
                    if ln.strip().startswith("import ") or ln.strip().startswith("from ")]
    blob = "\n".join(import_lines).lower()
    for token in _FORBIDDEN:
        assert token not in blob, f"{mod.__name__} must not import '{token}'"


def test_collector_does_not_pull_trading_modules_into_sys_modules_on_import():
    # Re-import freshly and assert the trading runtime is not transitively imported by our modules.
    import importlib
    for name in ("data.public_spot_fetchers", "data.reference_collector"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    assert "main_loop" not in sys.modules, "importing the collector must not import main_loop"
