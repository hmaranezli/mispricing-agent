"""phase6_1/b3_depth_evidence_mapping.py — Phase 6.1 B3 depth-evidence identity pass-through.

The smallest possible B3 boundary: one pure function that returns a B2 material's
``depth_source_reference`` exactly as received (or ``None``). It reads no file, parses nothing, builds
nothing, and concludes nothing. The depth record is sealed evidence carried by identity; this module
never inspects its fields, constructs no object, and imports no reader, no Phase 5, and no Shadow
Intent. Authored under ``docs/handoff/phase6_1_b3_depth_evidence_mapping_tdd_slice_charter.md``.
"""


def depth_evidence_reference_from_material(material):
    """Return ``material.depth_source_reference`` exactly as-is: the same depth-evidence object when
    present (preserved by identity, never copied or reconstructed), or ``None`` when absent — nothing
    is invented in its place. No field of the depth record is inspected here."""
    return material.depth_source_reference
