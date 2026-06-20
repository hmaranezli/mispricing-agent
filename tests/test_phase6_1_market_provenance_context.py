"""tests/test_phase6_1_market_provenance_context.py — Phase 6.1 MarketProvenanceContext passive DTO.

Pins the frozen, immutable, methodless ten-field passive provenance envelope defined in
`docs/handoff/phase6_1_market_provenance_context_field_shape_charter.md`. The DTO carries exactly ten
supplied non-payload provenance attributes; its only method is `__post_init__`, a structural guard that
enforces ONLY exact-str/non-empty for the nine string fields and exact-int/non-negative for
`retrieval_epoch_ms`. It parses nothing, derives nothing, defaults nothing, validates no semantic
vocabulary, mints no identity, and never references S2 identity.

Forbidden tokens/identifiers appearing in THIS test file are explicit fixtures; the runtime module must
contain none of them.
"""
import ast

import pytest
from dataclasses import fields, FrozenInstanceError

import phase6_1
from phase6_1.market_provenance_context import MarketProvenanceContext


_MODULE_BASENAME = "market_provenance_context.py"

_EXPECTED_FIELDS = (
    "source_artifact",
    "source_field",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "retrieval_epoch_ms",
    "raw_snapshot_identity",
)

_STRING_FIELDS = (
    "source_artifact",
    "source_field",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "raw_snapshot_identity",
)


def _kwargs(**overrides):
    base = dict(
        source_artifact="artifact-x",
        source_field="field-x",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="venue:perp",
        venue_buy="venue-a",
        venue_sell="venue-b",
        retrieval_epoch_ms=1_750_000_000_001,
        raw_snapshot_identity="market-snap-abc",
    )
    base.update(overrides)
    return base


def _ctx(**overrides):
    return MarketProvenanceContext(**_kwargs(**overrides))


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

def test_constructs_and_exposes_all_ten_fields_verbatim():
    kw = _kwargs()
    ctx = MarketProvenanceContext(**kw)
    for name in _EXPECTED_FIELDS:
        assert getattr(ctx, name) == kw[name]


def test_exact_ten_field_surface_in_order():
    names = tuple(f.name for f in fields(MarketProvenanceContext))
    assert names == _EXPECTED_FIELDS
    assert len(names) == 10


# --- immutability / slots -------------------------------------------------------------------------

def test_is_frozen_immutable():
    ctx = _ctx()
    with pytest.raises(FrozenInstanceError):
        ctx.base_asset = "ETH"


def test_uses_slots_and_has_no_instance_dict():
    assert hasattr(MarketProvenanceContext, "__slots__")
    assert tuple(MarketProvenanceContext.__slots__) == _EXPECTED_FIELDS
    ctx = _ctx()
    assert not hasattr(ctx, "__dict__")


# --- structural guard: string fields --------------------------------------------------------------

def test_rejects_non_str_for_each_string_field():
    for name in _STRING_FIELDS:
        for bad in (1, 1.0, None, b"bytes", ["x"], ("x",), True):
            with pytest.raises(TypeError):
                MarketProvenanceContext(**_kwargs(**{name: bad}))


def test_rejects_empty_string_for_each_string_field():
    for name in _STRING_FIELDS:
        with pytest.raises(ValueError):
            MarketProvenanceContext(**_kwargs(**{name: ""}))


# --- structural guard: retrieval_epoch_ms ---------------------------------------------------------

def test_rejects_non_int_retrieval_epoch():
    for bad in ("1750000000001", 1.0, None, True, b"1"):
        with pytest.raises(TypeError):
            MarketProvenanceContext(**_kwargs(retrieval_epoch_ms=bad))


def test_rejects_negative_retrieval_epoch():
    with pytest.raises(ValueError):
        MarketProvenanceContext(**_kwargs(retrieval_epoch_ms=-1))


def test_accepts_zero_retrieval_epoch():
    ctx = _ctx(retrieval_epoch_ms=0)
    assert ctx.retrieval_epoch_ms == 0


# --- no semantic validation, no normalization (arbitrary non-empty strings accepted verbatim) -----

def test_accepts_arbitrary_nonempty_strings_without_semantic_validation():
    weird = _kwargs(
        source_artifact="!!!",
        source_field="???",
        base_asset="not-a-real-asset",
        quote_asset="   ",            # whitespace-only is non-empty and accepted (no trim)
        instrument_id="literally anything 123",
        venue_scope="UNScopedNonsense",
        venue_buy="x",
        venue_sell="y",
        raw_snapshot_identity="market-id::weird/value",
    )
    ctx = MarketProvenanceContext(**weird)
    for name in _STRING_FIELDS:
        assert getattr(ctx, name) == weird[name]


def test_does_not_normalize_or_mutate_string_values():
    ctx = _ctx(base_asset="  Btc  ", venue_buy="MiXeDcAsE")
    # stored verbatim: no trim, no upper/lower casing, no derivation
    assert ctx.base_asset == "  Btc  "
    assert ctx.venue_buy == "MiXeDcAsE"


# --- dual-identity ban: no S2 reference -----------------------------------------------------------

def test_module_does_not_reference_s2_identity():
    text = _module_text()
    assert "S2IdentityWiringCandidate" not in text
    assert "s2_identity_wiring_candidate" not in text


# --- AST-enforced bans (constraint 8) -------------------------------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_banned_modules():
    roots = _import_roots(_module_tree())
    for forbidden in {"re", "uuid", "datetime", "time", "hashlib", "os", "pathlib", "io", "sys",
                      "json", "logging"}:
        assert forbidden not in roots, forbidden


def test_module_has_no_banned_calls_or_attributes():
    banned = {"split", "strip", "lower", "upper", "replace", "format", "str", "repr", "hash", "id",
              "open", "print", "eval", "exec", "isinstance"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned, node.attr


def test_module_defines_no_function_or_method_except_post_init():
    func_names = []
    for node in ast.walk(_module_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_names.append(node.name)
    assert func_names == ["__post_init__"], func_names


def test_module_uses_no_method_decorators():
    # no staticmethod / classmethod / property / cached_property helper surfaces
    banned_decorators = {"staticmethod", "classmethod", "property", "cached_property"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                name = dec.id if isinstance(dec, ast.Name) else getattr(dec, "attr", None)
                assert name not in banned_decorators, name


def test_module_defines_only_the_one_dto_class():
    class_names = [n.name for n in ast.walk(_module_tree()) if isinstance(n, ast.ClassDef)]
    assert class_names == ["MarketProvenanceContext"], class_names
