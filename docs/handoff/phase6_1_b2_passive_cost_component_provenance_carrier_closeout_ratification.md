# Phase 6.1 B2 Passive Cost-Type Carrier Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It ratifies the **completed** B2 passive cost-type
> carrier TDD slice (commit `c5b842e`) and **freezes its invariants** before any downstream B3/Phase 5 work. It
> authorizes NO runtime, NO tests, NO lock-test edits, NO B3 runtime/tests, NO Phase 5 runtime/tests, NO Master
> B3 wiring, NO Phase 5 integration, NO B4 scoring, NO durable logs, NO `edge_direction`, NO
> `staleness_threshold_ms`, NO Shadow Intent, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify.
> **It defines no vocabulary values and authorizes nothing executable.** It is subordinate to
> `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_charter.md`,
> `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `c5b842ead02b69f696f8a1ca0d1a6ebc078ab73b`

---

## 1. Base / Dependency Chain

**Base commit:** `c5b842ead02b69f696f8a1ca0d1a6ebc078ab73b`.

References:

- `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_charter.md` — specified the passive
  carrier contract this slice implemented.
- `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md` — verdict **B**
  (closed vocabulary NOT necessary for Phase 6.1; label is passive provenance, economics in signed magnitude).
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md` — values **BLOCKED**.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — cells 1/2/4/5 ratified; Cell 3 gated.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — Master-B3 critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

**Implemented artifact under closeout (commit `c5b842e`, parent `c701a22`):** the optional
`cost_component_provenance_reference` field on `NormalizedEvidenceFieldBinding` in
`phase6_1/b2_normalization_contract.py`, validated by `_require_optional_cost_component_provenance_reference`,
threaded through `make_normalized_evidence_field_binding` (keyword, default `None`).

---

## 2. Why This Closeout Exists

The B2 passive cost-type carrier slice is implemented and green. Before any downstream B3 route or Phase 5
integration is even chartered, its behavioral guarantees must be **frozen as ratified invariants** so that no
later step can silently widen the field from passive provenance into a semantic/actionable contract. This
charter records the proof, ratifies the invariants, and binds the forward B3 constraint — without authorizing
any further build.

---

## 3. Proof Summary (from commit `c5b842e`)

- **RED → GREEN:** tests authored first. RED run: **30 failed, 11 passed** — exact failure mode
  `TypeError: make_normalized_evidence_field_binding() got an unexpected keyword argument
  'cost_component_provenance_reference'` and `AssertionError: runtime function
  '_require_optional_cost_component_provenance_reference' not found` (feature genuinely missing, not a typo).
  Minimal runtime added → GREEN.
- **Targeted pytest result:** **326 passed in 66.82s** across
  `tests/test_phase6_1_b2_normalization_contract.py`, `tests/test_phase6_1_b2_replay_normalization.py`,
  `tests/test_phase6_1_forbidden_token_locks.py`, `tests/test_phase6_1_diagnostic_ev_non_actionability.py`.
  **No broad pytest** was run.
- **Intermediate RED note:** the forbidden-token locks (one slice-local, two package-wide) caught descriptive
  words `fee` / `rebate` / `live` in the runtime **docstrings**; the prose was reworded (e.g. "economics reside
  entirely in the signed magnitude"), a **documentation-only** change with **no logic change**, after which all
  326 passed.
- **Changed files (exactly two):** `phase6_1/b2_normalization_contract.py`,
  `tests/test_phase6_1_b2_normalization_contract.py`.

---

## 4. Ratified Invariants (frozen)

### 4.1 — B2 carrier is passive-only
`cost_component_provenance_reference` is **passive provenance metadata only**. It MUST never drive control flow,
branching, scoring, routing, sizing, execution, `edge_direction`, verdicts, thresholds, or any Phase 5 gate
outcome. **RATIFIED.**

### 4.2 — Optionality / absence contract
- `None` means **absent** (the default; carried as `None`).
- A present value is an **exact non-empty, non-whitespace `str`**, carried **verbatim** (no strip/case
  normalization — surrounding whitespace around real content is preserved exactly).
- Empty / whitespace-only strings are **rejected** (`B2NormalizationValueError`).
- `UNKNOWN` / `OTHER` / `UNSPECIFIED` / `MISC` / catch-all absence sentinels are **forbidden**; absence is
  `None` only and carries no default meaning. **RATIFIED.**

### 4.3 — Signed magnitude ⊥ provenance (orthogonality)
- A **positive** magnitude implies **no** label.
- A **negative** magnitude implies **no** label.
- A **zero** magnitude implies **no** absence (a `"0"` magnitude may still carry a label).
- The label does **not** alter the magnitude, unit, role, names, or any non-provenance field.
- Proven behaviorally: across 7 differing labels (incl. `spread`/`slippage`/`gas`/`funding` fixtures) every
  non-provenance field was byte-for-byte identical; only the verbatim label differed. **RATIFIED.**

### 4.4 — No vocabulary validation
No enum / `frozenset` / allowed-set / membership check on the field; **no fixture promotion**
(`TAKER_FEE`/`MAKER_REBATE` remain test fixtures, never contract); no closed-set semantics. Proven by a
negative-lock asserting the validator contains no `frozenset`/`set`/`Enum` and no `in`/`not in` membership.
**RATIFIED.**

### 4.5 — No polarity inference
The label does **not** imply fee/rebate/cost/reduction or any directional/arithmetic behavior; cost economics
reside **entirely** in the signed decimal magnitude (sign = polarity). **RATIFIED.**

### 4.6 — No numeric parsing or derivation
No `Decimal`/`int`/`float`/`complex` behavior for this field; no JSON/base64/container parsing; not derived from
`normalized_field_name`/`source_field`/`binding_role`/unit/magnitude/sign/position. Proven by a negative-lock
scoping the validator's AST for forbidden coercion/serialization calls. **RATIFIED.**

### 4.7 — No forbidden surface added
The runtime adds **no** `b3`, `phase5`, `ShadowIntent`, `capacity`/`CapacityConstraintGate`, or
`live`/actionability tokens (proven by slice-local and package-wide forbidden-token locks, all green).
**RATIFIED.**

### 4.8 — Backward-compatibility seal
- Existing replay/artifact readers remain compatible: the new factory parameter is keyword-only with default
  `None`, so all existing call sites are unchanged.
- Older/existing records implicitly map to **`None`** (absent) via that default.
- `tests/test_phase6_1_b2_replay_normalization.py` **did not require modification** and remained green.
  **RATIFIED.**

---

## 5. Master B3 Forward Invariant (binding on any future route)

Because B2 treats `cost_component_provenance_reference` as **strictly passive provenance**, any future Master B3
route MUST also treat it passively. B3 is **forbidden** from introducing, on the basis of this field: vocabulary
validation, closed-set/enum checks, polarity inference, numeric/JSON/base64 parsing, normalization, branching,
scoring, routing, or any actionability. If ever authorized, B3 may **only carry/pass the value through verbatim
(or `None`)**. This forward constraint is **RATIFIED**; it authorizes no B3 route by itself.

---

## 6. Master B3 Remains Blocked

This closeout does **not** authorize any Master B3 route or wiring. Cell 3's cost-type sub-blocker is now reduced
to *"a separately-authorized router-only B3 pass-through under §5"*, but that remains ungranted. The separate
Master-B3 blockers **`edge_direction`** (Shadow Intent Envelope track) and **`staleness_threshold_ms`** remain
**untouched and out of scope**. **Master B3 wiring stays BLOCKED.**

---

## 7. Effect on B2 Cost-Type Carrier Status

- **Status: BUILT and RATIFIED (passive provenance).** The carrier exists, is green, and its invariants are
  frozen by §4.
- No further B2 change is authorized by this charter. Any change to the field's behavior would require a new,
  separately-authorized charter and must not violate the §4 invariants.

---

## 8. Preserved Upstream Decisions (unchanged)

- **Closed vocabulary NOT necessary for Phase 6.1** (necessity verdict B) — preserved.
- **Owner = Phase 5; mechanism = M3** — preserved. A future closed vocabulary, if ever needed, must still be
  ratified under M3 (authoritative values charter → later Phase 5 runtime lock). This passive carrier neither
  performs nor pre-empts that closure.
- **Vocabulary values — still BLOCKED.**

---

## 9. Required Future Proof Before Any B3 Route

Before a Master B3 cost-type route may be chartered, a future separately-authorized step must establish: (1) a
**router-only** B3 pass-through honoring §5 (verbatim or `None`, no validation/inference/parsing/branching);
(2) independent resolution of `edge_direction` and `staleness_threshold_ms`; and (3) no Phase 5 vocabulary
closure presumed (Phase 5 still consumes the label only as free-form provenance, economics in signed magnitude).

---

## 10. Proof / Changed-Files Record (audit)

- **Final commit:** `c5b842ead02b69f696f8a1ca0d1a6ebc078ab73b`; **parent:** `c701a22c299a610bdeac2595e7b2e9499e96cb97`.
- **Changed files:** `phase6_1/b2_normalization_contract.py` (field + validator + factory keyword + closed-
  contract assert), `tests/test_phase6_1_b2_normalization_contract.py` (+30 tests).
- **Targeted pytest:** 326 passed in 66.82s; no broad pytest; no graphify.

---

## 11. Still-Forbidden Work

- **No** vocabulary values defined/proposed/endorsed; **no** fixture promotion; **no** fallback/catch-all value.
- **No** runtime change; **no** test change; **no** lock-test edit.
- **No** B3 runtime/tests; **no** B3 route designed; **no** Master B3 wiring; **no** Phase 5 runtime/tests; **no**
  Phase 5 integration; **no** B4 scoring; **no** durable logs; **no** output carrier; **no** Shadow Intent; **no**
  live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.
- **No** reversal or weakening of the ratified owner (Phase 5) or mechanism (M3).

---

## 12. Next Safe Step

- A **separate review** to decide whether to authorize a **router-only Master B3 cost-type pass-through
  charter** under the §5 forward invariant — carrying the verbatim provenance string (or `None`) with no
  validation/inference/parsing/branching — bearing in mind Master B3 also remains blocked on the independent
  `edge_direction` and `staleness_threshold_ms` resolutions.
- **No implementation is authorized by this charter.** Any B3 route, Phase 5 integration, Phase 5 vocabulary
  closure (under M3, if ever needed), B4 scoring, durable logs, the live adapter, Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
