"""phase6_1/cell3_passive_cost_context_source.py — Phase 6.1 Cell-3 passive cost-context source.

A zero-argument, hermetic, deterministic generator of the passive zero-cost substrate ratified in
``docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md``. It assembles ONE
passive cost-validity context — EXCLUSIVELY through the frozen Phase 5 factories
``make_observable_cost_observation`` and ``make_observable_cost_validity_context`` — from fixed string
constants, and returns it as an exact length-1 tuple.

It is a passive TEST-SUBSTRATE, not a real fee model: the cost magnitude is a carried constant ``"0"``
with an explicit, honest declared zero-cost evidence string — never a computed zero, and never a real
fee schedule, maker/taker, VIP tier, venue fee table, discount, spread, or slippage. It performs no
arithmetic and no edge evaluation; it reads no clock, config, or environment; it mints no identity and
crosses no market or system identity plane; it holds no iteration, no buffering, no re-attempt, and no
durable medium. One call with no inputs returns one length-1 tuple.
"""
from phase5.observable_cost_friction_boundary import make_observable_cost_observation
from phase5.pre_net_edge_calculation_input_boundary import make_observable_cost_validity_context


CELL3_PASSIVE_COST_CONTEXT_SOURCE_COMPONENT_NAME = "phase6_1_cell3_passive_cost_context_source"

# --- §4a cost-observation hermetic constants (ratified 0dd398f) -----------------------------------
_COMPONENT_NAME = "phase6_1_cell3_passive_cost_context_source"
_ORIGIN_COMPONENT = "phase6_1_cell3_passive_cost_context_source"
_ORIGIN_RESULT_STATUS = "OBSERVED"
_STATUS = "OBSERVABLE_COST_OBSERVED"
_COST_COMPONENT_TYPE = "PASSIVE_ZERO_COST_SUBSTRATE"
_SIGNED_DECIMAL_VALUE = "0"
_UNIT = "proportion"
_SOURCE_CONTRACT = "phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"
_SOURCE_ARTIFACT = "docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"
_SOURCE_FIELD = "passive_zero_cost_substrate.signed_decimal_value"
_ZERO_COST_EVIDENCE = "DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED"
_BOUNDARY_VERSION = "phase6_1.cell3_passive_cost_context_source.v0"

# --- §4b cost-validity-context hermetic constants -------------------------------------------------
_VALID_FROM_EPOCH_MS = "0"
_VALID_UNTIL_EPOCH_MS = "0"
_VALIDITY_SOURCE_CONTRACT = "phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"
_VALIDITY_SOURCE_ARTIFACT = (
    "docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"
)
_VALIDITY_SOURCE_FIELD = "passive_zero_cost_substrate.validity_interval"
_VALIDITY_ASSERTION_TYPE = "DECLARED_PASSIVE_SUBSTRATE_NO_REAL_VALIDITY_WINDOW"


def build_passive_zero_cost_validity_contexts():
    """Return the exact length-1 tuple ``(context,)`` of one passive zero-cost validity context.

    Takes no inputs. Builds the observation and its validity context ONLY through the frozen Phase 5
    factories, which own all field validation (exact-type, non-empty, canonical decimal, explicit-zero
    evidence, integer-string bounds). Nothing is derived, computed, formatted, or minted.
    """
    cost_observation = make_observable_cost_observation(
        component_name=_COMPONENT_NAME,
        origin_component=_ORIGIN_COMPONENT,
        origin_result_status=_ORIGIN_RESULT_STATUS,
        status=_STATUS,
        cost_component_type=_COST_COMPONENT_TYPE,
        signed_decimal_value=_SIGNED_DECIMAL_VALUE,
        unit=_UNIT,
        source_contract=_SOURCE_CONTRACT,
        source_artifact=_SOURCE_ARTIFACT,
        source_field=_SOURCE_FIELD,
        zero_cost_evidence=_ZERO_COST_EVIDENCE,
        boundary_version=_BOUNDARY_VERSION,
    )
    cost_validity_context = make_observable_cost_validity_context(
        cost_observation=cost_observation,
        valid_from_epoch_ms=_VALID_FROM_EPOCH_MS,
        valid_until_epoch_ms=_VALID_UNTIL_EPOCH_MS,
        validity_source_contract=_VALIDITY_SOURCE_CONTRACT,
        validity_source_artifact=_VALIDITY_SOURCE_ARTIFACT,
        validity_source_field=_VALIDITY_SOURCE_FIELD,
        validity_assertion_type=_VALIDITY_ASSERTION_TYPE,
        boundary_version=_BOUNDARY_VERSION,
    )
    return (cost_validity_context,)
