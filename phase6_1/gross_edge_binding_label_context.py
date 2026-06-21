"""phase6_1/gross_edge_binding_label_context.py — Phase 6.1 GrossEdgeBindingLabelContext passive DTO.

A frozen, immutable, methodless passive micro-container carrying exactly two externally-supplied
GROSS_EDGE binding labels for the pass-path ingestion boundary. Built under
``docs/handoff/phase6_1_gross_edge_binding_label_context_field_shape_charter.md``.

It is pure data. The only method is ``__post_init__``, a structural guard enforcing ONLY that both
attributes are exact non-empty ``str``. It parses nothing, splits nothing, trims nothing, normalizes no
case, infers nothing, defaults nothing, casts nothing, and validates no vocabulary or semantic meaning.
Both values are supplied verbatim by the caller.

``source_field`` is the **binding-level** raw source field of the GROSS_EDGE binding only; it is never
copied, reused, inferred, aliased, or defaulted from any record-level source field. This module imports,
references, and type-hints no broader-system carrier: no snapshot record, no identity carrier, no
provenance container, no normalizer. It carries no cost, no storage, and no runner logic. No clock, no
randomness, no hashing, no identity minting.
"""
from dataclasses import dataclass


GROSS_EDGE_BINDING_LABEL_CONTEXT_COMPONENT_NAME = "phase6_1_gross_edge_binding_label_context"


@dataclass(frozen=True, slots=True)
class GrossEdgeBindingLabelContext:
    """Frozen, methodless passive container: exactly two supplied GROSS_EDGE binding labels.

    ``normalized_field_name`` and ``source_field`` are each an exact non-empty string carried verbatim —
    nothing is parsed, split, trimmed, cased, derived, defaulted, or minted. ``source_field`` is
    binding-level only, never a record-level source field.
    """

    normalized_field_name: object
    source_field: object

    def __post_init__(self):
        for value in (self.normalized_field_name, self.source_field):
            if type(value) is not str:
                raise TypeError(
                    "GrossEdgeBindingLabelContext labels must each be an exact str"
                )
            if value == "":
                raise ValueError(
                    "GrossEdgeBindingLabelContext labels must each be non-empty"
                )
