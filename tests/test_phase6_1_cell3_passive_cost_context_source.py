"""tests/test_phase6_1_cell3_passive_cost_context_source.py — Phase 6.1 Cell-3 passive cost-context source.

Pins the zero-argument, hermetic, factory-only passive zero-cost substrate defined in
`docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md` (ratified `0dd398f`).
`build_passive_zero_cost_validity_contexts()` takes ZERO arguments and returns an exact length-1 tuple of
one `ObservableCostValidityContext`, assembled ONLY through the frozen Phase 5 factories
`make_observable_cost_observation` and `make_observable_cost_validity_context`, from fixed string
constants — no dynamic generation, no clock, no identity, no storage/runner logic, no real cost math.

Forbidden tokens/identifiers appearing in THIS test file are explicit fixtures; the runtime module must
contain none of them.
"""
import ast
import inspect

import phase6_1
from phase6_1.cell3_passive_cost_context_source import (
    build_passive_zero_cost_validity_contexts,
    CELL3_PASSIVE_COST_CONTEXT_SOURCE_COMPONENT_NAME,
)
from phase5.pre_net_edge_calculation_input_boundary import ObservableCostValidityContext
from phase5.observable_cost_friction_boundary import OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE
from phase5.net_edge_calculator_boundary import (
    make_passive_gross_edge_magnitude,
    make_passive_pre_net_edge_calculation_input,
)

# end-to-end peers (pass path: B2 ingestion -> normalizer -> B3 -> producer -> Phase 5)
from phase6_1.b2_pass_path_ingestion import ingest_pass_path_snapshot_record
from phase6_1.b2_replay_normalization import normalize_replay_snapshot_to_evidence_material
from phase6_1.b3_passive_client_wiring import wire_passive_shadow_input
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext


_MODULE_BASENAME = "cell3_passive_cost_context_source.py"

# The exact §4a ObservableCostObservation constants ratified in 0dd398f.
_OBS_CONSTANTS = {
    "component_name": "phase6_1_cell3_passive_cost_context_source",
    "origin_component": "phase6_1_cell3_passive_cost_context_source",
    "origin_result_status": "OBSERVED",
    "status": "OBSERVABLE_COST_OBSERVED",
    "cost_component_type": "PASSIVE_ZERO_COST_SUBSTRATE",
    "signed_decimal_value": "0",
    "unit": "proportion",
    "source_contract": "phase6_1_cell3_passive_cost_context_source_field_shape_charter.md",
    "source_artifact":
        "docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md",
    "source_field": "passive_zero_cost_substrate.signed_decimal_value",
    "zero_cost_evidence": "DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED",
    "boundary_version": "phase6_1.cell3_passive_cost_context_source.v0",
}

# The exact §4b ObservableCostValidityContext constants.
_CTX_CONSTANTS = {
    "valid_from_epoch_ms": "0",
    "valid_until_epoch_ms": "0",
    "validity_source_contract": "phase6_1_cell3_passive_cost_context_source_field_shape_charter.md",
    "validity_source_artifact":
        "docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md",
    "validity_source_field": "passive_zero_cost_substrate.validity_interval",
    "validity_assertion_type": "DECLARED_PASSIVE_SUBSTRATE_NO_REAL_VALIDITY_WINDOW",
    "boundary_version": "phase6_1.cell3_passive_cost_context_source.v0",
}


def _module_path():
    import pathlib  # test-only path resolution; the runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


def _the_function_def(tree):
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert len(funcs) == 1
    return funcs[0]


# --- output shape ---------------------------------------------------------------------------------

def test_returns_exact_length_one_tuple():
    result = build_passive_zero_cost_validity_contexts()
    assert type(result) is tuple
    assert len(result) == 1


def test_single_item_is_exact_observable_cost_validity_context():
    result = build_passive_zero_cost_validity_contexts()
    assert type(result[0]) is ObservableCostValidityContext


# --- hermetic constants carried verbatim ----------------------------------------------------------

def test_observation_constants_carried_verbatim():
    obs = build_passive_zero_cost_validity_contexts()[0].cost_observation
    for name, value in _OBS_CONSTANTS.items():
        assert getattr(obs, name) == value, name


def test_validity_context_constants_carried_verbatim():
    ctx = build_passive_zero_cost_validity_contexts()[0]
    for name, value in _CTX_CONSTANTS.items():
        assert getattr(ctx, name) == value, name


def test_zero_cost_evidence_is_explicit_not_the_not_applicable_sentinel():
    obs = build_passive_zero_cost_validity_contexts()[0].cost_observation
    assert obs.zero_cost_evidence != OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE
    assert obs.signed_decimal_value == "0"


def test_deterministic_constants_across_calls():
    a = build_passive_zero_cost_validity_contexts()[0]
    b = build_passive_zero_cost_validity_contexts()[0]
    assert a.cost_observation.signed_decimal_value == b.cost_observation.signed_decimal_value
    assert a.cost_observation.zero_cost_evidence == b.cost_observation.zero_cost_evidence
    assert a.validity_assertion_type == b.validity_assertion_type


def test_component_name_constant():
    assert CELL3_PASSIVE_COST_CONTEXT_SOURCE_COMPONENT_NAME == (
        "phase6_1_cell3_passive_cost_context_source"
    )


# --- accepted by the frozen Phase 5 downstream boundary -------------------------------------------

def test_tuple_accepted_by_frozen_pre_net_edge_boundary():
    gross_obs = make_passive_gross_edge_magnitude(gross_edge_value="7", gross_edge_unit="proportion")
    calc_input = make_passive_pre_net_edge_calculation_input(
        gross_observation=gross_obs,
        cost_validity_contexts=build_passive_zero_cost_validity_contexts(),
    )
    assert calc_input is not None
    assert calc_input.cost_validity_contexts is not None


def test_end_to_end_pass_through_b2_ingestion_b3_producer_keeps_net_equal_gross():
    provenance = MarketProvenanceContext(
        source_artifact="docs/handoff/replay_artifact_lines",
        source_field="replay.line",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="hyperliquid_perp",
        venue_buy="hyperliquid",
        venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_500,
        raw_snapshot_identity="market-identity-0001",
    )
    label = GrossEdgeBindingLabelContext(
        normalized_field_name="gross_edge_magnitude",
        source_field="raw.gross_magnitude",
    )
    payload = {
        "gross_magnitude": "7",
        "unit": "proportion",                       # identical token to the substrate's cost unit
        "venue": "hl",
        "pair": "BTC",
        "observed_at_epoch_ms": "1750000000000",
    }
    record = ingest_pass_path_snapshot_record(
        parsed_payload=payload,
        market_provenance_context=provenance,
        gross_edge_binding_label_context=label,
    )
    material = normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=record, evidence_epoch_tolerance_ms=0
    )
    out = wire_passive_shadow_input(
        normalized_evidence_material=material,
        cost_validity_contexts=build_passive_zero_cost_validity_contexts(),
    )
    assert type(out) is PassiveShadowInput
    assert out.net_edge_calculation_result.net_edge_value == "7"      # net == gross (zero cost)
    assert out.net_edge_calculation_result.total_cost_value == "0"


# --- AST: exact zero-argument signature -----------------------------------------------------------

def test_runtime_signature_is_zero_arguments():
    sig = inspect.signature(build_passive_zero_cost_validity_contexts)
    assert len(sig.parameters) == 0


def test_ast_function_has_no_args_varargs_kwargs_or_defaults():
    fn = _the_function_def(_module_tree())
    a = fn.args
    assert a.args == []
    assert a.posonlyargs == []
    assert a.kwonlyargs == []
    assert a.vararg is None
    assert a.kwarg is None
    assert a.defaults == []
    assert a.kw_defaults == []


# --- AST: factory-only imports, no raw dataclass ---------------------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_imports_only_the_two_allowed_phase5_factories():
    tree = _module_tree()
    assert _import_roots(tree) <= {"phase5"}
    imported_modules = set()
    imported_names = set()
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Import), "plain import is forbidden"
        if isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module)
            for alias in node.names:
                imported_names.add(alias.name)
    assert imported_modules <= {
        "phase5.observable_cost_friction_boundary",
        "phase5.pre_net_edge_calculation_input_boundary",
    }, imported_modules
    assert imported_names <= {
        "make_observable_cost_observation",
        "make_observable_cost_validity_context",
    }, imported_names


def test_no_raw_dataclass_import_or_construction():
    text = _module_text()
    for forbidden in (
        "ObservableCostObservation",
        "ObservableCostValidityContext",
        "@dataclass",
        "dataclasses",
        "object.__new__",
        "__setattr__",
    ):
        assert forbidden not in text, forbidden


# --- AST: literal constants present exactly --------------------------------------------------------

def test_literal_constants_present_exactly():
    text = _module_text()
    for value in list(_OBS_CONSTANTS.values()) + list(_CTX_CONSTANTS.values()):
        assert ('"' + value + '"') in text, value


# --- AST: no dynamic generation / no math / no loops / no isinstance -------------------------------

def test_no_dynamic_generation_or_string_math():
    banned_call_names = {
        "format", "uuid", "uuid1", "uuid4", "time", "hash", "getenv", "random", "randint",
        "token_hex", "token_bytes", "open", "eval", "exec", "compile", "input", "str", "int", "repr",
    }
    banned_attrs = {"format", "now", "uuid4", "getenv", "loads", "dumps", "join", "time"}
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, (ast.JoinedStr, ast.FormattedValue)), "f-string is forbidden"
        assert not isinstance(node, ast.BinOp), "no arithmetic / string concatenation"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_call_names, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned_attrs, node.attr


def test_no_loops_comprehensions_try_or_isinstance():
    banned_nodes = (ast.For, ast.AsyncFor, ast.While, ast.Try,
                    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, banned_nodes), type(node).__name__
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_defines_only_the_one_function_and_no_class():
    tree = _module_tree()
    func_names = [n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert func_names == ["build_passive_zero_cost_validity_contexts"], func_names
    class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert class_names == [], class_names


# --- text: no storage / runner / identity / actionability surface ---------------------------------

def test_module_has_no_storage_runner_identity_or_actionability_tokens():
    text = _module_text()
    for forbidden in (
        "S2IdentityWiringCandidate", "raw_snapshot_identity", "MarketProvenanceContext",
        "GrossEdgeBindingLabelContext", "ingest_pass_path", "Silver", "checkpoint", "cursor",
        "queue", "retry", "persist", "storage", "actionab", "readiness", "verdict",
    ):
        assert forbidden not in text, forbidden
