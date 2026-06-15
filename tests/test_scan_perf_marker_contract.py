"""tests/test_scan_perf_marker_contract.py — scan_perf log marker contract (TDD, observability hygiene).

`_scan_and_execute` her döngüde tek bir `[scan_perf] ...` satırı basıyor (total_ms / scan_edges_ms /
council_ms / execute_ms / candidates). Bu satır şu an inline f-string — test edilebilir bir seam YOK,
yani alan adları sessizce drift edebilir (E12a observation: scan_perf yalnız nokta-latency; offline
p95/p99 parsing bu alan adlarına bağımlı). Bu slice o sözleşmeyi pin'ler.

Hedef eksik seam:
    main_loop._format_scan_perf(total_ms, scan_edges_ms, council_ms, execute_ms, candidates) -> str

GREEN (AYRI adım) mevcut f-string'i bu helper'a DAVRANIŞ KORUNARAK çıkaracak (format DEĞİŞMEZ); call-site
helper'ı çağıracak. Bu RED yalnız sözleşmeyi sabitler — opsiyonel offline observability hijyeni, F/live
AÇMAZ. Metrics/cache/aggregation kodu YOK.

İlk RED: `_format_scan_perf` yok → AttributeError (eksik üretim seam'i; syntax/unrelated import DEĞİL).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main_loop


REQUIRED_FIELDS = ("total_ms=", "scan_edges_ms=", "council_ms=", "execute_ms=", "candidates=")


def test_format_scan_perf_seam_exists():
    """main_loop `_format_scan_perf` callable bir seam expose etmeli. RED: yok → AttributeError."""
    assert callable(main_loop._format_scan_perf)


def test_scan_perf_line_has_prefix():
    """Çıktı `[scan_perf]` prefix'iyle başlamalı."""
    line = main_loop._format_scan_perf(
        total_ms=12.0, scan_edges_ms=3.0, council_ms=4.0, execute_ms=5.0, candidates=2)
    assert line.startswith("[scan_perf]")


def test_scan_perf_line_has_all_required_fields():
    """Çıktı beş zorunlu alan etiketini de içermeli (sözleşme: total_ms/scan_edges_ms/council_ms/
    execute_ms/candidates). RED: helper yok → AttributeError."""
    line = main_loop._format_scan_perf(
        total_ms=12.0, scan_edges_ms=3.0, council_ms=4.0, execute_ms=5.0, candidates=2)
    missing = [f for f in REQUIRED_FIELDS if f not in line]
    assert not missing, f"scan_perf satırında eksik alan(lar): {missing}"


def test_scan_perf_ms_fields_rounded_int():
    """ms alanları mevcut format ile uyumlu olmalı (`:.0f` → ondalıksız tamsayı string)."""
    line = main_loop._format_scan_perf(
        total_ms=12.6, scan_edges_ms=3.4, council_ms=4.5, execute_ms=5.5, candidates=2)
    assert "total_ms=13" in line
    assert "scan_edges_ms=3" in line
    assert "candidates=2" in line


def test_scan_perf_candidates_reflects_value():
    """candidates alanı verilen değeri yansıtmalı."""
    line = main_loop._format_scan_perf(
        total_ms=1.0, scan_edges_ms=1.0, council_ms=1.0, execute_ms=1.0, candidates=7)
    assert "candidates=7" in line
