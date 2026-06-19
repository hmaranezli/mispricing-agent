"""phase6_1/provenance_chain_lock.py — Phase 6.1 Slice 0C passive provenance-chain lock.

Implements ONLY a small validation helper, `verify_provenance_chain`, plus its two boundary error
types. Authored under `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` (Slice 0C). It adds NO
new data carrier.

The lock proves the existing chain
    NetEdgeCalculationResult -> PassiveShadowInput -> ShadowObservation
is the exact original objects, by reading already-present fields only (O(1), no mutation, no
computation, no lazy property). On a valid chain it returns the three existing objects BY IDENTITY as
a plain tuple; nothing is copied, reconstructed, or re-instantiated.

It fails loudly for any non-`ShadowObservation` entry (dict, raw Phase 5 object, halt carrier,
subclass) with `ShadowProvenanceTypeError`, and for a structurally-broken chain with
`ShadowProvenanceChainError`. Both are type/provenance boundary errors — NOT actionability verdicts.
A wrong entry is a misdirected type, never an actionability event.
No IO, no network, no clock, no env, no randomness.
"""
from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase6_1.shadow_observation import ShadowObservation


class ShadowProvenanceTypeError(TypeError):
    """Raised when the chain entry is not an exact ShadowObservation (wrong/misdirected type)."""


class ShadowProvenanceChainError(TypeError):
    """Raised when an exact ShadowObservation carries a structurally-broken provenance link."""


def verify_provenance_chain(chain_entry):
    """Validate and return the exact chain objects by identity.

    Reads already-present fields only. Returns
    ``(net_edge_calculation_result, passive_shadow_input, shadow_observation)`` — the same existing
    objects by reference — when the chain is exact at every link. Raises
    :class:`ShadowProvenanceTypeError` for a non-exact entry (dict, raw Phase 5 object, halt carrier,
    or subclass) and :class:`ShadowProvenanceChainError` for a broken nested link. Exact-type guards
    only (``type(value) is ExactType``); no ``isinstance``; nothing is copied or derived.
    """
    if type(chain_entry) is not ShadowObservation:
        raise ShadowProvenanceTypeError(
            "provenance-chain entry must be an exact ShadowObservation, not {}".format(
                type(chain_entry).__name__
            )
        )

    passive_shadow_input = chain_entry.source
    if type(passive_shadow_input) is not PassiveShadowInput:
        raise ShadowProvenanceChainError(
            "ShadowObservation.source must be an exact PassiveShadowInput, not {}".format(
                type(passive_shadow_input).__name__
            )
        )

    net_edge_calculation_result = passive_shadow_input.net_edge_calculation_result
    if type(net_edge_calculation_result) is not NetEdgeCalculationResult:
        raise ShadowProvenanceChainError(
            "PassiveShadowInput.net_edge_calculation_result must be an exact "
            "NetEdgeCalculationResult, not {}".format(type(net_edge_calculation_result).__name__)
        )

    return (net_edge_calculation_result, passive_shadow_input, chain_entry)
