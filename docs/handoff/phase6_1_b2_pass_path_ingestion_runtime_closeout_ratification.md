# Phase 6.1 — B2 Pass-Path Ingestion Runtime Closeout & Ratification Charter

> **This is a docs-only closeout/ratification charter.** It formally seals the **already-built, already-pushed**
> B2 pass-path ingestion runtime (commit `168949a`). It **builds nothing**: no runtime code, no tests, no schema,
> no adapter. It authorizes NO new runtime, NO tests, NO lock-test edits, NO frozen-component edits, NO Cell-3
> runtime, NO S5 runtime, NO S1 storage, NO live/paper/canary, NO execution/actionability, NO pytest, NO graphify.
> It is subordinate to
> `docs/handoff/phase6_1_b2_pass_path_ingestion_mapping_contract_charter.md`,
> `docs/handoff/phase6_1_market_provenance_context_runtime_dto_closeout_ratification.md`,
> `docs/handoff/phase6_1_gross_edge_binding_label_context_runtime_dto_closeout_ratification.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `168949a6a90cd03e1753ebc0a9483a004b75188a`

**Sealed artifact:** commit `168949a` — `feat(phase6_1): add B2 pass-path ingestion mapping` (parent `982f0ef`).

---

## 1. Base / Purpose

**Base commit:** `168949a6a90cd03e1753ebc0a9483a004b75188a`.

With the B2 pass-path ingestion runtime now **BUILT** (`168949a`) via a clean RED→GREEN TDD cycle, this charter
**ratifies** that implementation as the permanent, frozen pass-path ingestion mapping standard. It records the
strict-2-file boundary, the evidence-first method, the 3-input exclusivity, the precision-safe and timestamp
seals, the singular GROSS_EDGE binding shape, the COST/Cell-3 non-smuggling, the testing discipline, the
verification facts, and the **precise pipeline state with all remaining gates intact**. It claims **no** new
capability and **no** pass-path completion.

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Strict 2-File Runtime Seal (ratified)

The implementation touched **exactly two files** and nothing else:

- `phase6_1/b2_pass_path_ingestion.py` — the new runtime mapping module;
- `tests/test_phase6_1_b2_pass_path_ingestion.py` — its 26-test pin.

**No** edit was made to any frozen component: **no** change to `b2_normalization_contract`
(`make_public_raw_snapshot_record` / `PublicRawSnapshotRecord`), `b2_replay_normalization`,
`market_provenance_context`, `gross_edge_binding_label_context`, the Option-B reader, S2, B3, Producer, Phase 5,
B4, S4, S1, S5, or **any** lock test. The boundary is a **new, separate, downstream** mapping client that feeds
the existing frozen constructor **as-is** — every value it supplies is already a legal
`make_public_raw_snapshot_record` argument. The five pre-existing untracked files were left untouched.

---

## 3. Evidence-First Ratification (ratified)

The runtime was authored **only after** inspecting the frozen contracts from source, never from assumption:

- `make_public_raw_snapshot_record` — its 14 keyword-only arguments, its exact-type/non-empty validators, and
  its anti-copy lock (`observed_at_epoch_ms != str(retrieval_epoch_ms)`).
- The B2 field-entry shape consumed by `b2_replay_normalization` — the required labels
  `normalized_field_name`, `source_field`, `binding_role`, `magnitude`, `unit`, with optional
  `zero_cost_evidence`, each carried as `(label, value)` pairs.
- `MarketProvenanceContext` (ten supplied non-payload fields) and `GrossEdgeBindingLabelContext` (the two
  GROSS_EDGE binding labels).
- Both package-wide lock tests (`test_phase6_1_forbidden_token_locks.py`,
  `test_phase6_1_diagnostic_ev_non_actionability.py`) verbatim, so the new module satisfies the forbidden-token,
  forbidden-import, no-`isinstance`, and name-surface scans.
- The concrete payload keys (`gross_magnitude`, `unit`, `venue`, `pair`) were taken from the **frozen reader's
  own happy-path test fixtures**, and `observed_at_epoch_ms` from the serialization field-shape charter §6 — a
  **grounded** key surface, never fabricated.

The tests reflect the **actual** frozen contract (including a test that round-trips the produced record through
the frozen `b2_replay_normalization`), not an assumed one.

---

## 4. 3-Input Exclusivity (ratified)

`ingest_pass_path_snapshot_record` consumes **exactly three keyword-only inputs** — `parsed_payload`,
`market_provenance_context` (exact `MarketProvenanceContext`), and `gross_edge_binding_label_context` (exact
`GrossEdgeBindingLabelContext`) — proven by an `inspect.signature` test (exact names, all KEYWORD_ONLY, no
defaults). There is **zero** S2 / Silver / identity-evidence / shadow-input / capacity leakage: an AST/text scan
test asserts the module references none of `S2IdentityWiringCandidate`, `identity_evidence`, Silver, shadow-input,
or capacity, and imports only the `phase6_1` root. `raw_snapshot_identity` is **Market Identity** sourced **only**
from `MarketProvenanceContext`, on a plane strictly separate from S2 System Identity.

---

## 5. Precision-Safe Ratification (ratified, permanent standard)

The strict **structural halt on a numeric magnitude** is ratified as the **permanent standard against precision
loss**:

- `gross_magnitude` and `unit` are **verbatim strings only**. A non-string magnitude — `float`, `int`, or `bool`
  (a JSON number already lossily float-parsed at the medium) — **HALTS** with `B2PassPathIngestionTypeError`,
  **never** coerced.
- The runtime performs **no** `float` / `int` / `Decimal` cast, **no** rounding, scaling, formatting, unit
  conversion, precision-changing reserialization, or arithmetic — AST-locked (a test bans those call names and
  bans `.loads`/`.dumps` attributes). A lossless decimal magnitude requires the artifact to author it as a string.

---

## 6. Timestamp Boundary Ratification (ratified)

`observed_at_epoch_ms` behavior is ratified:

- an exact **`str`** is carried **verbatim**;
- the **only** numeric carriage is the **single lossless** `non-negative int → canonical str` (`str(n)` for
  `n >= 0`, e.g. `0 → "0"`);
- a **`float`**, a **negative int**, or a **`bool`** (`type(True) is bool`, not int) **HALTS**
  (`B2PassPathIngestionTypeError` / `B2PassPathIngestionValueError`).

There is **no clock** and **no** `retrieval ← observed` (or `observed ← retrieval`) repair: `retrieval_epoch_ms`
and `observed_at_epoch_ms` are sourced independently, and the frozen B2 anti-copy lock is **surfaced**, never
repaired (a test asserts `observed == str(retrieval)` raises the frozen `B2NormalizationValueError`).

---

## 7. Singular GROSS_EDGE Binding Seal (ratified)

`field_payload` is **exactly one** GROSS_EDGE binding entry:

- `magnitude` / `unit` ← payload (verbatim strings, §5);
- `normalized_field_name` and binding-level `source_field` ← **`GrossEdgeBindingLabelContext` only**;
- `binding_role` ← the structural constant `"GROSS_EDGE"` (never evaluated, thresholded, ranked, scored, or
  derived from the magnitude);
- record-level provenance (`source_artifact`, record-level `source_field`, market identity, venue scope/buy/sell,
  assets, instrument, `retrieval_epoch_ms`) ← `MarketProvenanceContext` only.

The **binding-level `source_field` never aliases the record-level `source_field`** — ratified by a test that sets
the two to distinct values and asserts the record carries the record-level value while the normalized binding
carries the binding-level value. The produced entry round-trips through the frozen normalizer to exactly one
GROSS_EDGE binding.

---

## 8. No COST / Cell-3 Smuggling (ratified)

The runtime emits **no** COST binding, **no** cost object/dict/placeholder, and **no** Cell-3 arithmetic.
`field_payload` carries the single GROSS_EDGE entry and **no** `zero_cost_evidence` label; per the frozen
downstream rule a GROSS_EDGE binding's `zero_cost_evidence` is `None`, and the round-trip test asserts exactly
that. COST economics enter downstream via the Producer/B3 `cost_validity_contexts` argument — **not** a
`PublicRawSnapshotRecord` field — and **remain separately gated**.

---

## 9. Testing Discipline Seal (ratified)

- A **real RED→GREEN** cycle: RED was `ModuleNotFoundError` (the module genuinely absent), then a minimal GREEN
  implementation — not a test written against pre-existing code.
- The **docstring scrub** (removing the prose token "Silver" that tripped the module's own isolation test) was a
  **code-conformance** fix, **not** a test weakening: the assertion stood and the code was conformed to it, per
  the standing "conform the code, never weaken the test" precedent.
- The **`_UNSET` sentinel correction** to the test's `_ingest` helper was **mature test discipline**: the original
  `None` default sentinel collided with `None` as a value-under-test, silently substituting a valid default and
  hiding the `None` rejection path; switching to a distinct `_UNSET` sentinel proved the runtime genuinely rejects
  `None`. No assertion was relaxed; the runtime was correct throughout.

---

## 10. Verification Facts (ratified)

- New suite `tests/test_phase6_1_b2_pass_path_ingestion.py`: **26 passed / 26**.
- Lock tests + peer suites — `test_phase6_1_forbidden_token_locks.py`,
  `test_phase6_1_diagnostic_ev_non_actionability.py`, `test_phase6_1_b2_normalization_contract.py`,
  `test_phase6_1_b2_replay_normalization.py`, `test_phase6_1_market_provenance_context.py`,
  `test_phase6_1_gross_edge_binding_label_context.py`, and the new suite: **384 passed / 0 failed**.
- **Zero regressions.** **No** broad `pytest` run (scope was the new suite + the lock tests + the directly
  affected peer suites only).

---

## 11. Precise Pipeline State (ratified)

- **B2 pass-path ingestion runtime: BUILT + RATIFIED** (`168949a`).
- **The pass path is still NOT contract-complete.** The passive **cost-context (Cell-3)** source feeding the
  B3/Producer `cost_validity_contexts` argument remains **separately gated and unbuilt**; the **S1 storage-medium**
  charter remains separate. Producing one `PublicRawSnapshotRecord` does not complete the B4-consumable pass path.
- **S5 runtime: ineligible.** The halt path stays complete (three authorized halt carriers → S4 → S1
  `ObservationHaltRecord`); the S1 sink stays a **test-only reference sink**.
- **Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit
  sites**; `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity
  validated."
- **Phase 6.1: INCOMPLETE. Phase 6.2: NOT ready.** No 6.2/7.x/8.x work is implied.

---

## 12. Still-Forbidden Work

- **No** edit / widen / relax / refactor of any frozen module (§2); **no** boundary-as-S5; **no** loop / stream /
  routing / retry / repair / EOF / cursor / storage / trigger.
- **No** numeric math / `float` / `Decimal` / rounding / scaling / unit conversion / precision-changing
  reserialization (§5); **no** lossy magnitude coercion — string-only, halt otherwise.
- **No** fabrication/inference of `normalized_field_name` or binding-level `source_field`; **no** reuse of
  record-level `source_field` for the binding (§7).
- **No** COST entry, passive cost placeholder, cost/fee math, or Cell-3 assembly (§8); **no** capacity activation.
- **No** S2 identity import/inspect/derive/hash/stringify/collapse/fallback; **no** Silver tuple; **no**
  shadow-input/identity-evidence leakage (§4).
- **No** clock; **no** `retrieval ← observed` copy; **no** timestamp-as-identity.
- **No** runtime/tests/schema/storage; **no** Cell-3 runtime; **no** S5 runtime; **no** S1 storage; **no**
  live/paper/canary; **no** execution/actionability; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness
  claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized docs-only Cell-3 Passive Cost-Context Source Charter** — designing how the passive
  real-cost evidence (the B3/Producer `cost_validity_contexts` argument) is sourced, **without** authorizing any
  Cell-3 runtime, cost arithmetic, S5 runtime, S1 storage, live/paper/canary, or any execution/actionability.
- Independently, the **S1 storage-medium** charter remains separately gated.
- Only after **both** the pass path (ingestion + label-source + cost-context) **and** the halt path are
  contract-complete does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** the B2 pass-path ingestion runtime (`168949a`) is **ratified and sealed** — a strict-2-file,
evidence-first, pure stateless mapping from one Option-B `parsed_payload` **plus** one `MarketProvenanceContext`
**plus** one `GrossEdgeBindingLabelContext` to **one** exact `PublicRawSnapshotRecord` via the frozen
`make_public_raw_snapshot_record`, with **3-input exclusivity** (no S2/Silver/identity-evidence/shadow-input/
capacity leakage), a **permanent precision-safe seal** (numeric magnitude halts; verbatim strings only), a
ratified **timestamp boundary** (verbatim str or the single lossless non-negative-int→canonical-str; float/
negative/bool halt; no clock; no retrieval←observed repair), **one** GROSS_EDGE `field_payload` binding (labels
from the binding-label context, provenance from the provenance context, binding-level `source_field` never
aliasing the record-level one), **no COST/Cell-3 smuggling** (`zero_cost_evidence` stays `None`), and mature
**testing discipline** (real RED→GREEN, docstring scrub as code conformance, `_UNSET` sentinel correction).
Verification: **26/26** new, **384 passed / 0 failed** across locks + peers, zero regressions, no broad pytest.
**The pass path remains NOT contract-complete** (passive cost-context / Cell-3 source separately gated; S1 storage
separate); **S5 runtime remains ineligible**; **Phase 6.1 remains incomplete** and **Phase 6.2 not ready**. **No
executable work is authorized.**
