"""tests/test_phase6_1_gross_edge_binding_label_context.py — Phase 6.1 GrossEdgeBindingLabelContext DTO.

Pins the frozen, immutable, methodless two-field passive micro-container defined in
`docs/handoff/phase6_1_gross_edge_binding_label_context_field_shape_charter.md`. It carries exactly two
externally-supplied GROSS_EDGE binding labels — `normalized_field_name` and the binding-level
`source_field` — each an exact non-empty `str` carried verbatim. Its only method is `__post_init__`, a
structural guard. It parses nothing, derives nothing, defaults nothing, validates no vocabulary, and is
fully isolated from MarketProvenanceContext / record-level source_field / S2 identity / B2 / the snapshot
record / S5.

Forbidden tokens/identifiers appearing in THIS test file are explicit fixtures; the runtime module must
contain none of them.
"""
import ast

import pytest
from dataclasses import fields, FrozenInstanceError

import phase6_1
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext


_MODULE_BASENAME = "gross_edge_binding_label_context.py"

_EXPECTED_FIELDS = ("normalized_field_name", "source_field")


def _kwargs(**overrides):
    base = dict(
        normalized_field_name="gross_edge_magnitude",
        source_field="raw.gross_edge",
    )
    base.update(overrides)
    return base


def _ctx(**overrides):
    return GrossEdgeBindingLabelContext(**_kwargs(**overrides))


def _module_path():
    import pathlib  # test-only path resolution; the runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


# --- construction / field surface -----------------------------------------------------------------

def test_constructs_and_exposes_both_fields_verbatim():
    kw = _kwargs()
    ctx = GrossEdgeBindingLabelContext(**kw)
    assert ctx.normalized_field_name == kw["normalized_field_name"]
    assert ctx.source_field == kw["source_field"]


def test_exact_two_field_surface_in_order():
    names = tuple(f.name for f in fields(GrossEdgeBindingLabelContext))
    assert names == _EXPECTED_FIELDS
    assert len(names) == 2


# --- immutability / slots -------------------------------------------------------------------------

def test_is_frozen_immutable():
    ctx = _ctx()
    with pytest.raises(FrozenInstanceError):
        ctx.source_field = "other"


def test_uses_slots_and_has_no_instance_dict():
    assert hasattr(GrossEdgeBindingLabelContext, "__slots__")
    assert tuple(GrossEdgeBindingLabelContext.__slots__) == _EXPECTED_FIELDS
    ctx = _ctx()
    assert not hasattr(ctx, "__dict__")


# --- structural guard -----------------------------------------------------------------------------

def test_rejects_non_str_for_each_field():
    for name in _EXPECTED_FIELDS:
        for bad in (1, 1.0, None, b"bytes", ["x"], ("x",), True):
            with pytest.raises(TypeError):
                GrossEdgeBindingLabelContext(**_kwargs(**{name: bad}))


def test_rejects_empty_string_for_each_field():
    for name in _EXPECTED_FIELDS:
        with pytest.raises(ValueError):
            GrossEdgeBindingLabelContext(**_kwargs(**{name: ""}))


# --- verbatim carriage / no semantic validation ---------------------------------------------------

def test_accepts_arbitrary_nonempty_strings_without_semantic_validation():
    weird = _kwargs(
        normalized_field_name="!!!literally anything!!!",
        source_field="   ",  # whitespace-only is non-empty and accepted (no trim)
    )
    ctx = GrossEdgeBindingLabelContext(**weird)
    assert ctx.normalized_field_name == weird["normalized_field_name"]
    assert ctx.source_field == weird["source_field"]


def test_does_not_normalize_or_mutate_string_values():
    ctx = _ctx(normalized_field_name="  Gross_Edge  ", source_field="MiXeD.Source")
    assert ctx.normalized_field_name == "  Gross_Edge  "
    assert ctx.source_field == "MiXeD.Source"


# --- binding-level source isolation / cross-contamination ban -------------------------------------

def test_module_does_not_reference_market_provenance_or_record_level_carriers():
    text = _module_text()
    for forbidden in (
        "MarketProvenanceContext",
        "market_provenance_context",
        "S2IdentityWiringCandidate",
        "s2_identity_wiring_candidate",
        "PublicRawSnapshotRecord",
        "public_raw_snapshot_record",
        "raw_snapshot_identity",
        "b2_normalization",
        "b2_replay_normalization",
    ):
        assert forbidden not in text, forbidden


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_broader_system_or_banned_modules():
    roots = _import_roots(_module_tree())
    # no cross-contamination from the broader package, and no IO/clock/hash/serialization modules
    assert "phase6_1" not in roots
    assert "phase5" not in roots
    for forbidden in {"re", "uuid", "datetime", "time", "hashlib", "os", "pathlib", "io", "sys",
                      "json", "logging"}:
        assert forbidden not in roots, forbidden


# --- AST-enforced bans (constraint 10) ------------------------------------------------------------

def test_module_has_no_banned_calls_or_attributes():
    banned = {"isinstance", "split", "strip", "lower", "upper", "replace", "format", "str", "repr",
              "hash", "id", "open", "print", "eval", "exec", "compile", "__import__", "input"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned, node.attr


def test_module_defines_exactly_one_class_with_no_inheritance_bases():
    classes = [n for n in ast.walk(_module_tree()) if isinstance(n, ast.ClassDef)]
    assert [c.name for c in classes] == ["GrossEdgeBindingLabelContext"]
    assert classes[0].bases == []
    assert classes[0].keywords == []  # no metaclass / ABC keyword bases


def test_module_class_has_exactly_two_dataclass_fields():
    classes = [n for n in ast.walk(_module_tree()) if isinstance(n, ast.ClassDef)]
    ann_targets = [
        n.target.id
        for n in classes[0].body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
    ]
    assert ann_targets == list(_EXPECTED_FIELDS)


def test_module_defines_no_function_or_method_except_post_init():
    func_names = [
        n.name for n in ast.walk(_module_tree())
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert func_names == ["__post_init__"], func_names


def test_module_uses_no_method_decorators():
    banned_decorators = {"staticmethod", "classmethod", "property", "cached_property", "abstractmethod"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                name = dec.id if isinstance(dec, ast.Name) else getattr(dec, "attr", None)
                assert name not in banned_decorators, name
