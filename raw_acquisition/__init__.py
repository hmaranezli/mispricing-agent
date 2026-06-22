"""raw_acquisition — quarantined post-Phase-6.2 raw-only one-shot public-data acquisition package.

Inert / exportless package initializer. It re-exports nothing, imports nothing, performs no import-time side
effect, and exposes no public façade. The sole runtime lives in ``raw_acquisition.public_raw_capture`` and is
imported explicitly by callers. This package never opens, reads, imports, attaches, queries, mutates, or
initializes S1; it owns only one-shot public fetch, exact raw-byte capture, retrieval provenance, and the
isolated raw-capture ledger, terminating strictly at RAW_CAPTURED. It implements no projection, S1 ingestion,
scoring, outcomes, calibration, paper, execution, routing, wallet, orders, scheduler, or capacity behavior.
"""
