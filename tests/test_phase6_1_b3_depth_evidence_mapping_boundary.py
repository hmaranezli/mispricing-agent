"""tests/test_phase6_1_b3_depth_evidence_mapping_boundary.py — Phase 6.1 B3 negative-lock slice.

Characterization / negative-lock tests that enforce the B3 depth-evidence mapping boundary
WITHOUT implementing B3. Authored under
`docs/handoff/phase6_1_b3_depth_evidence_mapping_boundary_charter.md`.

There is no B3 runtime module at this base, so the per-B3-module scans are vacuously satisfied today.
To keep them from being vacuous (and to give them teeth for the day a B3 module IS added), every
structural detector below is first shown to FLAG a crafted violating snippet, then shown to find
NOTHING across the real B3 module set. A B3 module is any phase6_1 module whose basename marks it
"b3"; the locks scope to those files so they never false-positive on the existing B1/B2/Phase 5 runtime
(which legitimately names depth subfields, constructs Phase 5 carriers, etc.).

Forbidden identifiers/tokens appearing in THIS file are explicit test fixtures.
"""
import ast
import importlib
import os
import pathlib
import re

import pytest

import phase6_1


# --- discovery ------------------------------------------------------------------------------------

def _pkg_dir():
    return pathlib.Path(phase6_1.__file__).resolve().parent


def _all_runtime_files():
    return sorted(_pkg_dir().glob("*.py"))


def _is_b3_basename(basename):
    return "b3" in basename.lower()


# Exactly one B3 runtime basename is allowlisted: the minimal identity/provenance pass-through. Any
# other B3 module is forbidden. The negative-lock scans below apply to whatever B3 module is present
# (now the allowlisted one), so the boundary is enforced on the real module, not merely on its absence.
_ALLOWED_B3_BASENAMES = {"b3_depth_evidence_mapping.py"}


def _b3_runtime_files():
    """Every phase6_1 runtime module marked as a B3 module by basename."""
    return [p for p in _all_runtime_files() if _is_b3_basename(os.path.basename(str(p)))]


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _tree(path):
    return ast.parse(_read(path))


def _token_present(token, text):
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _import_modules(tree):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _referenced_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
    return names


def _defined_names(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
    return names


# --- 1. only the single allowlisted B3 module may exist -------------------------------------------

def test_only_allowlisted_b3_module_present():
    present = {os.path.basename(str(p)) for p in _b3_runtime_files()}
    assert present <= _ALLOWED_B3_BASENAMES, sorted(present - _ALLOWED_B3_BASENAMES)


def test_allowlisted_b3_module_imports_and_non_allowlisted_b3_name_fails():
    # The single allowlisted B3 module resolves; any other B3 module name must not exist.
    importlib.import_module("phase6_1.b3_depth_evidence_mapping")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("phase6_1.b3_depth_capacity_mapping")


# --- 2. no phase6_1 runtime file imports a B3 depth mapping/wiring module --------------------------

def _imports_b3(tree):
    hits = []
    for m in _import_modules(tree):
        low = m.lower()
        if low.startswith("phase6_1.b3") or ("b3" in low and "depth" in low) or (
            "b3" in low and "mapping" in low
        ):
            hits.append(m)
    return hits


def test_b3_import_detector_has_teeth():
    bad = ast.parse("from phase6_1.b3_depth_evidence_mapping import wire_depth\n")
    assert _imports_b3(bad)
    ok = ast.parse("from phase6_1.b2_normalization_contract import make_normalized_evidence_material\n")
    assert _imports_b3(ok) == []


def test_no_phase6_1_file_imports_b3_depth_mapping():
    offenders = []
    for path in _all_runtime_files():
        for m in _imports_b3(_tree(path)):
            offenders.append((os.path.basename(str(path)), m))
    assert offenders == [], "phase6_1 runtime imports B3 depth mapping: %r" % offenders


# --- 3. no B3/Phase 5/Shadow Intent object construction in any B3 module ---------------------------

_FORBIDDEN_CONSTRUCTION_NAMES = {
    "PassiveShadowInput", "make_passive_shadow_input",
    "ShadowObservation", "make_shadow_observation",
    "NetEdgeCalculationResult", "_make_net_edge_result",
    "ShadowIntentEnvelope", "make_shadow_intent_envelope",
}


def _construction_hits(tree):
    return _FORBIDDEN_CONSTRUCTION_NAMES & _referenced_names(tree)


def test_construction_detector_has_teeth():
    bad = ast.parse("x = make_passive_shadow_input(net_edge_calculation_result=None)\n")
    assert _construction_hits(bad)
    ok = ast.parse("y = some_identity_reference\n")
    assert _construction_hits(ok) == set()


def test_no_b3_module_constructs_forbidden_carriers():
    offenders = []
    for path in _b3_runtime_files():
        hits = _construction_hits(_tree(path))
        if hits:
            offenders.append((os.path.basename(str(path)), sorted(hits)))
    assert offenders == [], "B3 carrier/output construction: %r" % offenders


# --- 4. no depth subfield consumed by any B3 module -----------------------------------------------

_DEPTH_SUBFIELDS = (
    "observed_size", "size_unit", "depth_source_field", "depth_source_artifact",
    "depth_source_contract", "depth_snapshot_identity", "depth_observed_at_epoch_ms",
    "depth_retrieval_epoch_ms",
)


def _depth_subfield_hits(text):
    return [name for name in _DEPTH_SUBFIELDS if _token_present(name, text)]


def test_depth_subfield_detector_has_teeth():
    assert _depth_subfield_hits("v = record.observed_size\n")
    assert _depth_subfield_hits("v = record.depth_snapshot_identity\n")
    # the identity slot name itself is NOT a subfield, and must not false-positive
    assert _depth_subfield_hits("v = material.depth_source_reference\n") == []


def test_no_b3_module_inspects_depth_subfields():
    offenders = []
    for path in _b3_runtime_files():
        hits = _depth_subfield_hits(_read(path))
        if hits:
            offenders.append((os.path.basename(str(path)), hits))
    assert offenders == [], "B3 inspects depth subfields: %r" % offenders


# --- 5. no numeric parsing/coercion or arithmetic/comparison surface in any B3 module -------------

_NUMERIC_CALL_NAMES = {
    "Decimal", "int", "float", "complex", "round", "sum", "min", "max", "abs", "pow", "divmod",
}
_ARITH_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ORDER_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)


def _numeric_surface_hits(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _NUMERIC_CALL_NAMES:
                hits.append(("call", node.func.id))
        if isinstance(node, ast.BinOp) and isinstance(node.op, _ARITH_OPS):
            hits.append(("arith", type(node.op).__name__))
        if isinstance(node, ast.Compare) and any(isinstance(op, _ORDER_OPS) for op in node.ops):
            hits.append(("order", "compare"))
    return hits


def test_numeric_surface_detector_has_teeth():
    assert _numeric_surface_hits(ast.parse("x = float(observed)\n"))
    assert _numeric_surface_hits(ast.parse("x = a + b\n"))
    assert _numeric_surface_hits(ast.parse("x = a > b\n"))
    # identity / None checks are allowed and must not be flagged
    assert _numeric_surface_hits(ast.parse("x = a is None\n")) == []
    assert _numeric_surface_hits(ast.parse("x = type(a) is PublicDepthSourceRecord\n")) == []


def test_no_b3_module_has_numeric_surface():
    offenders = []
    for path in _b3_runtime_files():
        hits = _numeric_surface_hits(_tree(path))
        if hits:
            offenders.append((os.path.basename(str(path)), hits))
    assert offenders == [], "B3 numeric/arith/compare surface: %r" % offenders


# --- 6. no capacity / actionability surface in any B3 module --------------------------------------

_CAPACITY_ACTIONABILITY_TOKENS = (
    "capacity_pass_reference", "sizing", "allocation", "routing", "route", "execution", "execute",
    "order", "trade", "candidate", "signal", "score", "verdict", "threshold", "ranking", "rank",
    "actionability", "actionable", "exposure", "wallet", "balance", "paper", "live",
)
_BANNED_NAME_SUBSTRINGS = (
    "calculate", "compute", "derive", "score", "readiness", "actionability", "actionable",
    "recommendation", "verdict", "rank", "ranking", "threshold", "bucket", "clamp", "scale",
)


def _capacity_token_hits(text):
    return [tok for tok in _CAPACITY_ACTIONABILITY_TOKENS if _token_present(tok, text)]


def _banned_defined_name_hits(tree):
    hits = []
    for name in _defined_names(tree):
        low = name.lower()
        if any(tok in low for tok in _BANNED_NAME_SUBSTRINGS):
            hits.append(name)
    return hits


def test_capacity_actionability_detectors_have_teeth():
    assert _capacity_token_hits("reason = capacity_pass_reference\n")
    assert _capacity_token_hits("s = sizing\n")
    assert _banned_defined_name_hits(ast.parse("def score_threshold():\n    pass\n"))
    # benign provenance text must not be flagged
    assert _capacity_token_hits("note = 'depth provenance reference only'\n") == []


def test_no_b3_module_has_capacity_or_actionability_surface():
    offenders = []
    for path in _b3_runtime_files():
        text = _read(path)
        tok_hits = _capacity_token_hits(text)
        name_hits = _banned_defined_name_hits(_tree(path))
        if tok_hits or name_hits:
            offenders.append((os.path.basename(str(path)), tok_hits, name_hits))
    assert offenders == [], "B3 capacity/actionability surface: %r" % offenders


# --- 7. no IO / network / env / secrets in any B3 module ------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "open", "read", "json", "csv", "pathlib", "os", "sys", "io", "requests", "urllib", "http",
    "socket", "aiohttp", "websocket", "websockets", "subprocess", "ssl", "smtplib", "ftplib",
    "pickle", "shelve", "shutil", "tempfile",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}
_FORBIDDEN_ATTRS = {"environ", "getenv", "popen", "system"}


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _io_surface_hits(tree):
    hits = []
    hits.extend(("import", r) for r in (_import_roots(tree) & _FORBIDDEN_IMPORT_ROOTS))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _FORBIDDEN_CALL_NAMES:
                hits.append(("call", node.func.id))
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
            hits.append(("attr", node.attr))
    return hits


def test_io_surface_detector_has_teeth():
    assert _io_surface_hits(ast.parse("import json\n"))
    assert _io_surface_hits(ast.parse("fh = open(p)\n"))
    assert _io_surface_hits(ast.parse("x = os.environ\nimport os\n"))
    ok = ast.parse("from phase6_1.b2_normalization_contract import NormalizedEvidenceMaterial\n")
    assert _io_surface_hits(ok) == []


def test_no_b3_module_has_io_network_env_surface():
    offenders = []
    for path in _b3_runtime_files():
        hits = _io_surface_hits(_tree(path))
        if hits:
            offenders.append((os.path.basename(str(path)), hits))
    assert offenders == [], "B3 IO/network/env surface: %r" % offenders


# --- 8. missing depth stays None: no fabricated/synthetic depth carrier in any B3 module ----------

_DEPTH_FABRICATION_NAMES = {"make_public_depth_source_record"}
_SYNTHETIC_TOKENS = ("UNKNOWN", "synthetic", "fabricate", "fabricated", "backfill", "placeholder")


def _depth_fabrication_hits(tree, text):
    hits = list(_DEPTH_FABRICATION_NAMES & _referenced_names(tree))
    hits.extend(tok for tok in _SYNTHETIC_TOKENS if _token_present(tok, text))
    return hits


def test_depth_fabrication_detector_has_teeth():
    bad = "rec = make_public_depth_source_record(observed_size='1')\n"
    assert _depth_fabrication_hits(ast.parse(bad), bad)
    bad2 = "default = 'UNKNOWN'\n"
    assert _depth_fabrication_hits(ast.parse(bad2), bad2)
    ok = "ref = material.depth_source_reference\n"
    assert _depth_fabrication_hits(ast.parse(ok), ok) == []


def test_no_b3_module_fabricates_depth_carrier():
    offenders = []
    for path in _b3_runtime_files():
        hits = _depth_fabrication_hits(_tree(path), _read(path))
        if hits:
            offenders.append((os.path.basename(str(path)), hits))
    assert offenders == [], "B3 fabricates/synthesizes depth carrier: %r" % offenders


# --- closeout: B3 runtime remains entirely absent/blocked at this base ----------------------------

def test_b3_runtime_limited_to_allowlist():
    # Any B3-basename module present must be exactly the allowlisted single pass-through module.
    b3_present = {b for b in (os.path.basename(str(p)) for p in _all_runtime_files())
                  if _is_b3_basename(b)}
    assert b3_present <= _ALLOWED_B3_BASENAMES, sorted(b3_present - _ALLOWED_B3_BASENAMES)
