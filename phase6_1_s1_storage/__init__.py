"""phase6_1_s1_storage — quarantined durable-storage package for the Phase 6.1 S1 audit trail.

This package is deliberately SEPARATE from the pure-logic ``phase6_1/`` package. It is the only place that
touches ``sqlite3``, disk I/O, and the canonical-text-payload encoding for durable persistence; the pure
``phase6_1/`` passive package stays completely ignorant of storage. Authored under
``docs/handoff/phase6_1_s1_durable_storage_field_shape_schema_charter.md``.
"""
