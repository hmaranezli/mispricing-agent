"""phase5/net_edge_profitability_gate_boundary.py — FIRST carrier slice of the
`phase5_net_edge_profitability_gate_boundary` component: `ProfitabilityThresholdPolicyContext`.

This implements ONLY the atomic `ProfitabilityThresholdPolicyContext` — a frozen, anti-truthiness,
anti-coercion carrier of explicit threshold policy data and provenance — plus a misrouted halt-carrier
guard. Per the planning artifact (`phase5_net_edge_profitability_gate_implementation_planning.md`):

- it is NOT `NetEdgeProfitabilityGate`, NOT `net_edge_profitability_preflight`, NOT a comparator/
  calculator, and performs no IO/network/env/datetime/random/subprocess;
- it carries declared threshold metadata only: it does NOT compare `threshold_value` to zero, does
  NOT interpret profitability, does NOT compare `threshold_unit` to any result unit, does NOT parse
  provenance, and does NOT compute/infer/default a threshold (no hardcoded/env/config/file/db value);
- every field is an exact, non-empty, non-whitespace `str` (`type(value) is str`; str subclasses
  rejected); `threshold_value` is a canonical signed decimal string (no leading zeros, no exponent,
  no surrounding whitespace), preserved verbatim — negative, zero, and positive are all valid policy
  data (no sign morality);
- it asserts no edge, no profitability, no readiness, no actionability, and no source truth.
"""
import re

from dataclasses import dataclass, fields as _dataclass_fields
from decimal import Decimal

from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)
from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult
from phase5.const import (
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    BLOCKED_NEEDS_EVIDENCE,
    NEXT_ACTION_OBTAIN_EVIDENCE,
)

PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME = "phase5_net_edge_profitability_gate_boundary"
BOUNDARY_VERSION = "phase5.net_edge_profitability_gate_boundary.v0"

# Canonical signed decimal string: optional leading '-', integer part with no leading zeros
# (a lone '0' or a non-zero-leading run of digits), optional '.' + one-or-more digits. No exponent,
# no leading '+', no surrounding whitespace, no bare '.'.
_CANONICAL_SIGNED_DECIMAL = re.compile(r"-?(0|[1-9]\d*)(\.\d+)?")

_FIELD_NAMES = (
    "component_name",
    "threshold_value",
    "threshold_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "policy_id",
    "boundary_version",
)


class ProfitabilityThresholdPolicyTruthinessError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is used in a truthiness/length context."""


class ProfitabilityThresholdPolicyCoercionError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is coerced to a number, string, or bytes."""


class ProfitabilityThresholdPolicyConstructionError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is constructed with a rejected/missing value."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the net-edge profitability gate boundary."""


@dataclass(frozen=True, repr=False, init=False)
class ProfitabilityThresholdPolicyContext:
    """A frozen, anti-coercion carrier of explicit profitability-threshold policy data and provenance.

    Construct only through :func:`make_profitability_threshold_policy_context`. Direct/positional
    construction is not supported. This context carries the declared threshold value/unit and its
    provenance; it proves no profitability and is not a comparator.
    """

    component_name: object
    threshold_value: object
    threshold_unit: object
    source_contract: object
    source_artifact: object
    source_field: object
    policy_id: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise ProfitabilityThresholdPolicyTruthinessError(
            "ProfitabilityThresholdPolicyContext must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise ProfitabilityThresholdPolicyTruthinessError(
            "ProfitabilityThresholdPolicyContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to int."
        )

    def __float__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to float."
        )

    def __complex__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to complex."
        )

    def __index__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to an index."
        )

    def __str__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to str."
        )

    def __bytes__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to bytes."
        )

    # --- safe debug repr only (safe identifiers; no threshold value or sensitive provenance leak) ---
    def __repr__(self):
        return (
            "ProfitabilityThresholdPolicyContext(component_name={!r}, policy_id={!r})".format(
                self.component_name, self.policy_id
            )
        )


def make_profitability_threshold_policy_context(
    *,
    component_name,
    threshold_value,
    threshold_unit,
    source_contract,
    source_artifact,
    source_field,
    policy_id,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`ProfitabilityThresholdPolicyContext`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses and non-str scalars/containers are rejected). ``threshold_value`` must additionally be a
    canonical signed decimal string (no leading zeros, no exponent) and is preserved verbatim; negative,
    zero, and positive values are all valid (no sign comparison, no zero check, no normalization). No
    provenance parsing, no unit/threshold inference, and no defaulting are performed. Error messages use
    only field names and ``type(value).__name__`` — never ``str(value)`` or ``repr(value)``.
    """
    provided = {
        "component_name": component_name,
        "threshold_value": threshold_value,
        "threshold_unit": threshold_unit,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "policy_id": policy_id,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None:
            raise ProfitabilityThresholdPolicyConstructionError(
                "required field {!r} must not be None".format(name)
            )
        # Exact-type check (not isinstance): str subclasses, bool/int/float/Decimal, containers, and
        # arbitrary objects are all rejected. Never call str/repr/eq on the value.
        if type(value) is not str:
            raise ProfitabilityThresholdPolicyConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ProfitabilityThresholdPolicyConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    # Canonical signed decimal string only — preserved verbatim; no Decimal/float, no normalization,
    # no zero/sign comparison.
    if _CANONICAL_SIGNED_DECIMAL.fullmatch(threshold_value) is None:
        raise ProfitabilityThresholdPolicyConstructionError(
            "field 'threshold_value' must be a canonical signed decimal string"
        )

    context = object.__new__(ProfitabilityThresholdPolicyContext)
    for name, value in provided.items():
        object.__setattr__(context, name, value)
    return context


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the net-edge profitability gate boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a threshold policy).
    - Anything else → return ``None`` (a non-halt no-op); subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, converted, unwrapped,
    serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/bytes), repr'd,
    equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "net-edge profitability gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "net-edge profitability gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None


# ---------------------------------------------------------------------------
# NetEdgeProfitabilityGate V1 / net_edge_profitability_preflight
#
# A pure, offline, deterministic profitability-threshold gate over exactly one NetEdgeCalculationResult
# and one ProfitabilityThresholdPolicyContext. The only arithmetic is a single local Decimal comparison
# (net_edge_value >= threshold_value) from already-canonical strings. Outputs are exactly: input
# identity (pass), an existing BlockedPacket (missing/malformed/unit-mismatch policy evidence), or an
# existing NoEligibleHaltPacket (below threshold). No new carrier/wrapper; never returns a packet for a
# programmatic wrong-path/misroute.
# ---------------------------------------------------------------------------

GATE_SOURCE_CONTRACT = "phase5_net_edge_profitability_gate_implementation_planning.md"
GATE_SOURCE_ARTIFACT = "docs/handoff/phase5_net_edge_profitability_gate_implementation_planning.md"

# Pinned reason vocabulary (planning-fixed; no aliases).
NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY = "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY"
NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY = "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY"
NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH = "NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH"
NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD = "NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD"

# No-eligible packet literals (below-threshold is the only V1 no-eligible market fact here).
_NO_ELIGIBLE_STATUS = "NO_ELIGIBLE"
_NO_ELIGIBLE_NEXT_ACTION = "HALT_BYPASS_NO_ELIGIBLE"

# net_edge_value as produced by the calculator: canonical decimal string (no exponent).
_RESULT_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")

# The exact field set the policy carrier must carry (read from its dataclass definition).
_POLICY_REQUIRED_FIELDS = tuple(f.name for f in _dataclass_fields(ProfitabilityThresholdPolicyContext))

_MISSING = object()


class NetEdgeProfitabilityGateTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the profitability gate."""


def _gate_blocked(*, reason_code, missing_or_invalid_field):
    """Build a gate BlockedPacket via the existing factory — no new packet class, no wrapper."""
    return make_blocked_packet(
        component_name=PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME,
        origin_component=PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME,
        origin_result_status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status=BLOCKED_NEEDS_EVIDENCE,
        reason_code=reason_code,
        missing_or_invalid_field=missing_or_invalid_field,
        source_contract=GATE_SOURCE_CONTRACT,
        source_artifact=GATE_SOURCE_ARTIFACT,
        source_field=reason_code,
        deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
        human_review_required=True,
        may_retry_after_evidence=True,
        created_from_contract=GATE_SOURCE_CONTRACT,
        boundary_version=BOUNDARY_VERSION,
    )


def _gate_no_eligible():
    """Build the gate NoEligibleHaltPacket via the existing factory — below-threshold only."""
    return make_no_eligible_halt_packet(
        component_name=PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME,
        origin_component=PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME,
        origin_result_status=_NO_ELIGIBLE_STATUS,
        status=_NO_ELIGIBLE_STATUS,
        no_eligible_reason=NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD,
        source_contract=GATE_SOURCE_CONTRACT,
        source_artifact=GATE_SOURCE_ARTIFACT,
        source_field=NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD,
        deterministic_next_action=_NO_ELIGIBLE_NEXT_ACTION,
        boundary_version=BOUNDARY_VERSION,
    )


def net_edge_profitability_preflight(*, calculation_result, threshold_policy):
    """Pure profitability-threshold gate over one NetEdgeCalculationResult and one policy context.

    Returns the identical ``calculation_result`` on pass (``net_edge_value >= threshold_value``, equality
    passes); an existing :class:`BlockedPacket` for missing/malformed/unit-mismatch threshold policy
    evidence; and an existing :class:`NoEligibleHaltPacket` only when below threshold. Programmatic
    wrong-path / wrong-type inputs raise :class:`NetEdgeProfitabilityGateTypeError` or
    :class:`MisroutedHaltCarrierError` and never produce a packet. See
    ``phase5_net_edge_profitability_gate_implementation_planning.md`` for the pinned contract.
    """
    # --- Programmatic wrong-path / wrong-type first ---
    reject_misrouted_halt_carrier(calculation_result)
    reject_misrouted_halt_carrier(threshold_policy)
    if type(calculation_result) is not NetEdgeCalculationResult:
        raise NetEdgeProfitabilityGateTypeError(
            "net_edge_profitability_preflight requires an exact NetEdgeCalculationResult, not "
            + type(calculation_result).__name__
        )
    if type(threshold_policy) is not ProfitabilityThresholdPolicyContext:
        raise NetEdgeProfitabilityGateTypeError(
            "net_edge_profitability_preflight requires an exact ProfitabilityThresholdPolicyContext, not "
            + type(threshold_policy).__name__
        )

    # --- Malformed result internal state → programmatic gate TypeError (never a market packet) ---
    # Only reachable via a factory-bypassed result; the planning artifact has no packet reason for it.
    net_value = getattr(calculation_result, "net_edge_value", _MISSING)
    net_unit = getattr(calculation_result, "net_edge_unit", _MISSING)
    if (net_value is _MISSING or type(net_value) is not str
            or _RESULT_CANONICAL_DECIMAL.fullmatch(net_value) is None):
        raise NetEdgeProfitabilityGateTypeError(
            "NetEdgeCalculationResult.net_edge_value is not a canonical decimal string"
        )
    if net_unit is _MISSING or type(net_unit) is not str or net_unit.strip() == "":
        raise NetEdgeProfitabilityGateTypeError(
            "NetEdgeCalculationResult.net_edge_unit is not a non-empty string"
        )

    # --- Policy evidence: missing required fields (factory bypassed) → BlockedPacket ---
    for name in _POLICY_REQUIRED_FIELDS:
        value = getattr(threshold_policy, name, _MISSING)
        if value is _MISSING or type(value) is not str or value.strip() == "":
            return _gate_blocked(
                reason_code=NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY,
                missing_or_invalid_field="threshold_policy",
            )

    # --- Policy evidence: malformed threshold_value (factory bypassed) → BlockedPacket ---
    threshold_value = threshold_policy.threshold_value
    if _CANONICAL_SIGNED_DECIMAL.fullmatch(threshold_value) is None:
        return _gate_blocked(
            reason_code=NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY,
            missing_or_invalid_field="threshold_value",
        )

    # --- Unit policy: case-sensitive exact match only → BlockedPacket on mismatch ---
    if net_unit != threshold_policy.threshold_unit:
        return _gate_blocked(
            reason_code=NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH,
            missing_or_invalid_field="threshold_unit",
        )

    # --- Single Decimal comparison from already-canonical strings (no float, no rounding) ---
    if Decimal(net_value) < Decimal(threshold_value):
        return _gate_no_eligible()

    # --- Pass: return the identical result object by identity (no wrap/copy/enrich/mutate) ---
    return calculation_result


class NetEdgeProfitabilityGate:
    """Stateless, non-carrier namespace for the net-edge profitability gate.

    Carries no state and requires no construction; the runtime entrypoint is the pure function
    :func:`net_edge_profitability_preflight`, exposed here as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(net_edge_profitability_preflight)
