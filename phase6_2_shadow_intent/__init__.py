"""phase6_2_shadow_intent — quarantined Phase 6.2 reconstruction package (Slice A onward).

This downstream package consumes caller-supplied S1 append-order replay rows read-only and the verified
sealed scenario-definition artifact. No Phase 6.1 module imports it; it never modifies S5, S1,
``phase6_1/``, ``phase6_1_s1_storage/``, the frozen DTOs, or any lock test. Slice A introduces only the
logical model (``logical_model``); predicates, the atomic replay step, and the reconstruction fold are
later, separately-authorized slices.
"""
