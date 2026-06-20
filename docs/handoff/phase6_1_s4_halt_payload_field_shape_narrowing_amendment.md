# Phase 6.1 — S4 Halt-Payload Field-Shape Narrowing Amendment

> **This is a docs-only amendment.** It **narrows** one risky logical observation attribute of the S4 halt payload
> **before any runtime implementation exists** — it renames/narrows `halt_inputs_summary` to
> `opaque_upstream_context` and tightens its contract. It **designs and builds nothing**. It authorizes NO runtime
> code, NO tests, NO schema/runtime/interface edits, NO storage/persistence/serialization design, NO taxonomy, NO
> actionability, NO S5 runner, NO Cell-3 assembly, NO Phase 6.2 work, NO pytest, NO graphify, NO edits to the
> Option-B reader / `S2IdentityWiringCandidate` / B3 / B4 / the S1 reference sink. It **amends** (and is subordinate
> to) `docs/handoff/phase6_1_s4_halt_payload_field_shape_charter.md`, and is further subordinate to
> `docs/handoff/phase6_1_s4_exception_routing_halt_materialization_decision_charter.md`,
> `docs/handoff/phase6_1_b4_score_payload_field_shape_charter.md`,
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern, and **this amendment governs over the base field-shape charter for the single
> attribute it narrows**.

**Base:** `c6f48f60d76ef171f8523aa0fc6ba4323e616a91`

---

## 1. Base / Dependency Chain

**Base commit:** `c6f48f60d76ef171f8523aa0fc6ba4323e616a91`.

References:

- `…_s4_halt_payload_field_shape_charter.md` — defined the **narrow, closed three-attribute** halt payload
  (`halt_origin_reference`, `halt_inputs_summary`, `halt_family_descriptor`). This amendment **narrows the middle
  attribute only**, leaving the other two and the closed-set discipline unchanged.
- `…_s4_exception_routing_halt_materialization_decision_charter.md` — the **Mortician Rule** (records an
  already-observed halt; never retries, repairs, normalizes, enriches, back-fills, or **synthesizes missing data**);
  the halt carrier is consumed **opaquely by reference**.
- `…_b4_score_payload_field_shape_charter.md` — the peer discipline mirrored throughout.

**No capacity validation and no capacity pass is claimed by this amendment** (see §6).

---

## 2. Why Narrow (the risk in `halt_inputs_summary`)

The base attribute name **`halt_inputs_summary`** is **risky before runtime exists**: the word "summary" invites a
runtime to *produce* a summary — i.e. to read the halt carrier, format it, stringify an exception, paste error
text/args/`repr`, or assemble an arbitrary descriptive bag. That would silently breach the base charter's §7a
(no stack-trace/error-text dumping), §6 (no open dictionary surface), and the Mortician Rule (no synthesis). The
attribute is therefore **renamed and narrowed now**, while it is still purely conceptual, so no runtime can drift
into producing context.

---

## 3. Narrowing: `halt_inputs_summary` → `opaque_upstream_context`

### 3a. Rename (binding)
The middle Logical Observation Attribute is **renamed** from `halt_inputs_summary` to **`opaque_upstream_context`**.
The name `halt_inputs_summary` is **retired** and must **not** appear in any future S4 runtime, schema, or test as a
payload attribute. The closed three-field payload shape (§4) is preserved.

### 3b. Tightened contract (binding)
`opaque_upstream_context` is **passive, opaque, by-reference context only**:

- It MUST be **either** pre-existing passive upstream context carried **by reference** (e.g. already-present
  passive **venue/pair** context that the upstream passive pipeline already produced) **or** `None`.
- It MUST **NOT** be free text, a constructed description, a human-readable "summary," dynamic error text,
  traceback-derived content, exception **args / message / `repr` / `str`** output, log lines, or an **arbitrary
  dict** / open key-value bag.
- It MUST **NOT** inspect, read, parse, classify, or interpret `halt_source` (the observed halt carrier) **to create
  context**. Context is **borrowed where it already exists upstream**, never **manufactured from the halt**. If no
  such pre-existing passive context exists, the attribute is **`None`** — it is never back-filled, defaulted, or
  synthesized (Mortician Rule).
- It carries **no identity** and **no actionability** (§5), and is never promoted to identity.

### 3c. Relationship to the halt carrier
- The **opaque halt carrier** remains carried — opaquely, by reference — **only** through `halt_origin_reference`
  (unchanged). `opaque_upstream_context` is **not** a second channel for the carrier and must never duplicate,
  rephrase, stringify, or derive from it. The two attributes stay strictly separate: origin reference = *which
  opaque halt*, upstream context = *pre-existing passive context the halt was observed in (or `None`)*.

---

## 4. Closed Three-Field Payload Shape (preserved)

The halt `family_payload` remains a **narrow, closed set of exactly three** Logical Observation Attributes — no
addition, no open dictionary surface (base charter §6 unchanged):

- **`halt_origin_reference`** — *(unchanged)* opaque, by-reference link to the already-observed halt carrier; origin
  provenance, **not identity**; never parsed/stringified/repr'd/repaired.
- **`opaque_upstream_context`** — *(narrowed, this amendment)* pre-existing passive upstream context by reference
  (e.g. already-present venue/pair), **or `None`**; never free text / error text / traceback / exception args-
  message-repr-str / arbitrary dict; never derived from `halt_source`.
- **`halt_family_descriptor`** — *(unchanged)* non-versioned replay-explainability descriptor; **not** a versioned/
  runtime ID, **not** identity, **not** a severity/priority/taxonomy label.

These remain **Logical Observation Attributes** — **not** database columns, serialized keys, JSON structure,
dataclass fields, Python types, SQL/Parquet schema, indexes, primary keys, or persistence formats.

---

## 5. Preserved Invariants (restated, binding)

All base field-shape invariants remain in force and are **not** loosened by this amendment:

- **No stack-trace / error-text dumping** — no dynamic error messages, parsed error strings, exception `repr`/`str`/
  args, traceback text, stack frames, frame locals, or debugger-style logs anywhere in the payload (base §7a),
  reinforced for `opaque_upstream_context` by §3b.
- **No taxonomy invention** — no severity/priority/criticality/`WARNING`-`CRITICAL`-`FATAL`/retry-class/route-class/
  recoverability/halt-ranking (base §7b).
- **No fallback identity** — payload never duplicates/derives/aliases/replaces S2 identity; identity stays
  **envelope-level only** via `identity_evidence`; no synthesized key even when data is missing (base §5).
- **No arbitrary key/value bag / open dictionary surface** — closed named set only; no `details`/`context`/`extra`/
  `raw` catch-all (base §6); `opaque_upstream_context` is **not** such a bag (§3b).
- **No actionability** — no route/retry/repair/readiness/verdict/order/execution/allocation/priority/ranking/
  severity/candidate/opportunity; no "should continue / should stop / should retry / should trade" (base §7c).
- **Peer symmetry** — `ObservationHaltRecord` stays a first-class **equal peer** of `ObservationScoreRecord` (base
  §9); this amendment changes no envelope field and no peer relationship.
- **S5 isolation** — the **S5 runner is not designed or implemented** here; this amendment touches only the halt
  payload field-shape.
- **Frozen upstream** — the Option-B reader, `S2IdentityWiringCandidate`, B3, B4, and the S1 reference sink remain
  **frozen**; this amendment edits no code and no other charter.

---

## 6. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 7. Still-Forbidden Work

- **No** runtime code, tests, schema, serialization, or persistence; **no** edits to the reader / S2 / B3 / B4 / S1 /
  S5; **no** edits to any other charter file.
- **No** free text / dynamic error text / traceback / exception args-message-repr-str / log lines / arbitrary dict in
  `opaque_upstream_context`; **no** context manufactured by inspecting `halt_source` (§3b).
- **No** stack-trace dumping, taxonomy/severity invention, fallback/aliased identity, or open dictionary surface
  (§5).
- **No** fourth attribute; **no** widening of the closed three-field shape; **no** re-introduction of the retired
  name `halt_inputs_summary`.
- **No** actionability; **no** "should continue / should stop / should retry" implication.
- **No** S5 runner / orchestration; **no** storage medium / persistence; **no** Cell-3 assembly.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 8. Next Safe Step

- A **separately-authorized S4 halt-materialization runtime TDD slice** — implementing, **under the (now-amended)
  field-shape and the S4 decision charter**, a pure/deterministic passive materializer that consumes an
  **already-observed** halt carrier (opaquely, by reference) plus the **existing** `S2IdentityWiringCandidate`,
  carries identity opaquely at the envelope level, and populates the closed three-attribute `family_payload`
  (`halt_origin_reference`, **`opaque_upstream_context`** [pre-existing passive context by reference or `None`,
  never derived from the carrier], `halt_family_descriptor`), constructing one `ObservationHaltRecord` for the S1
  reference sink — test-first, Mortician Rule honored (no retry/repair/back-fill/synthesis), no stack-trace dumping,
  no taxonomy, no actionability, no S5 runner, no storage, handling any runtime halt-name lock collision via its own
  separately-authorized exception.
- Independently/subsequently: the **S5 runner**; the **S1 storage-medium** charter; the **real-cost Cell-3**
  assembly. Each separately gated.
- **No implementation is authorized by this amendment.**

**Conclusion:** the risky `halt_inputs_summary` attribute is **renamed and narrowed to `opaque_upstream_context`**
**before any runtime exists** — now strictly **pre-existing passive upstream context by reference (e.g. already-
present venue/pair) or `None`**, and explicitly **never** free text, dynamic error text, traceback-derived content,
exception args/message/`repr`/`str`, or an arbitrary dict, and **never** manufactured by inspecting `halt_source`.
The halt `family_payload` keeps its **closed three-field shape** (`halt_origin_reference`, `opaque_upstream_context`,
`halt_family_descriptor`), and all base invariants hold: **no** stack-trace dumping, **no** taxonomy/severity, **no**
fallback identity, **no** open key/value bag, **no** actionability, **peer symmetry** preserved, **S5 isolation**
preserved, **frozen upstream**. The retired name `halt_inputs_summary` must not reappear. It is **docs-only** and
**designs no schema/runtime/storage**; existing modules remain **frozen**; Phase 6.1 remains **incomplete** and
Phase 6.2 **not ready**. **No executable work is authorized.**
