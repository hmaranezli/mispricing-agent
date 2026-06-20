# Phase 6.1 — Pass-Path Edge Contract Charter (Docs-Only BLOCKER)

> **This is a docs-only, evidence-first decision charter that resolves to a BLOCKER.** It investigates the missing
> pass-path edge identified in `568b93a` (§6 of the S5 Runner Planning Charter) — how an Option-B reader **parsed
> payload** could legally reach the frozen passive pass path that ultimately yields a `PassiveShadowInput` for B4 —
> and, on the evidence, **records why no payload-only translation boundary is definable yet and STOPS**. It
> **designs and builds nothing**: no runtime, no tests, no schema, no adapter. It authorizes NO runtime code, NO
> tests, NO schema/runtime/interface edits, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 /
> S1 / S5 / lock-tests, NO normalization adapter, NO S5 runtime, NO storage, NO Cell-3 assembly, NO Phase 6.2 work,
> NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s5_runner_planning_charter.md`,
> `docs/handoff/phase6_1_b4_passive_scoring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s4_halt_materialization_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `568b93a7bfce4e73ed4c5b83cae4a12902933d8f`

---

## 1. Base / Purpose

**Base commit:** `568b93a7bfce4e73ed4c5b83cae4a12902933d8f`.

The S5 planning charter (§6) surfaced an unresolved gap: the Option-B reader emits a structurally-parsed payload,
but B4 consumes an exact `PassiveShadowInput`, and no ratified frozen edge connects them. This charter does the
**evidence-first** investigation that §6 required, then decides — **on repo evidence, not assumption** — whether a
standalone, stateless, payload-only **Strict Translation Boundary** can legally bridge that gap.

**Verdict (this charter): BLOCKER.** No payload-only translation boundary is definable, because the real gap is
**B2-level ingestion normalization** (plus a non-payload cost dependency). The missing work is classified below as a
**separate, separately-gated B2/pass-path ingestion-normalization contract decision**, not a thin adapter and not
S5.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Evidence-First Pass-Path Trace (verified from repo symbols)

The frozen pass path was traced from B4 **upstream**, reading each component's exact consumed type directly from
source (no assumption that the target is B2):

1. **B4** — `phase6_1/b4_passive_scoring.py` :: `build_passive_observation_record(*, pass_handoff, identity_evidence,
   opaque_cost_context)` admits an **exact `PassiveShadowInput`** (`type(pass_handoff) is not PassiveShadowInput` →
   `TypeError`).
2. **`PassiveShadowInput`** — `phase6_1/passive_shadow_input.py` :: `make_passive_shadow_input(*,
   net_edge_calculation_result, source_venue, source_pair, observed_at_epoch_ms)`; the result field must be an exact
   Phase 5 `NetEdgeCalculationResult`.
3. **Producer** — `phase6_1/passive_producer.py:32` :: `produce_passive_shadow_input(*, gross_edge_value,
   gross_edge_unit, cost_validity_contexts, source_venue, source_pair, observed_at_epoch_ms)`. It builds a canonical
   gross magnitude, requires a **non-empty exact `cost_validity_contexts` tuple**, runs `calculate_net_edge`, and
   returns a `PassiveShadowInput` (or a defensive carrier by identity). It **re-validates and derives nothing of its
   own** beyond delegating to the canonical factories.
4. **B3 (master client)** — `phase6_1/b3_passive_client_wiring.py:29` :: `wire_passive_shadow_input(*,
   normalized_evidence_material, cost_validity_contexts)` admits an **exact `NormalizedEvidenceMaterial`**
   (`type(...) is not NormalizedEvidenceMaterial` → `B3PassiveClientWiringError`). It reads the single `GROSS_EDGE`
   binding's magnitude/unit and the raw snapshot's venue/pair/observed-epoch **by exact field access** and forwards
   `cost_validity_contexts` verbatim. It **derives nothing**.
5. **B2 replay normalizer** — `phase6_1/b2_replay_normalization.py:95` ::
   `normalize_replay_snapshot_to_evidence_material(*, raw_snapshot, evidence_epoch_tolerance_ms,
   depth_source_reference=None)` admits an **exact `PublicRawSnapshotRecord`** and returns a
   `NormalizedEvidenceMaterial`.
6. **B2 raw carrier** — `phase6_1/b2_normalization_contract.py` :: `make_public_raw_snapshot_record(...)` builds the
   exact `PublicRawSnapshotRecord`. Its `field_payload` must be a **non-empty `tuple` of field-entries** — each a
   `tuple` of exact **two-item `(label, value)` string pairs** — carrying the required B2 label vocabulary
   (`normalized_field_name`, `source_field`, `binding_role`, `magnitude`, `unit`); **every label and value must be a
   non-empty `str`**; magnitudes are carried **verbatim as exact strings** (no Decimal/float/int parsing);
   `binding_role` is an **exact-vocabulary** string (`GROSS_EDGE`, …); provenance epochs are **canonical
   unsigned-int strings**. `_require_tuple_only` **rejects `list`/`dict`/`set`** outright (anti-coercion).
7. **Option-B reader (the source)** — `phase6_1/option_b_event_stream_reader.py:84-87` :: each physical line is
   parsed via `json.loads(line)` into an **arbitrary parsed payload** (on a valid line) or an
   `OptionBLocalParseHalt` (on a malformed line). The reader performs **no semantic/business validation** and
   guarantees **no B2 shape**.

**The earliest frozen pass-path input contract** an externally-supplied payload must satisfy is therefore the
construction of an exact **`PublicRawSnapshotRecord`** (step 6) — which is **already a structured, labeled, exactly
typed B2 carrier**, not a raw external blob. The B2 replay normalizer (step 5) consumes that carrier; it does **not**
consume a raw parsed payload.

---

## 3. Why a Payload-Only Strict Translation Boundary Is NOT Definable

A Strict Translation Boundary (per the request's constraint 4) would have to be **standalone, stateless,
deterministic, payload-only**, mapping **structural payload fields** into the exact existing pass-path input
**without** computing edge/score/cost/intent/identity/timestamps/business semantics and (constraint 7) **without
normalization, coercion, defaulting, unit math, or schema repair**. Against the evidence of §2, bridging an Option-B
`json.loads` payload to the earliest frozen input (`PublicRawSnapshotRecord`) would unavoidably require:

- **Shape repair.** Arbitrary parsed JSON (a dict/list of JSON scalars) → the exact B2 shape of a non-empty
  **tuple** of field-entries, each a **tuple** of two-item `(label, value)` pairs. JSON arrays deserialize to Python
  **`list`**, which `_require_tuple_only` **rejects**; turning `list → tuple` is **coercion**.
- **Type coercion.** JSON numbers deserialize to `int`/`float`, but B2 requires every magnitude/value as an exact
  **`str`** (magnitudes carried verbatim, no parsing). Converting JSON scalars to canonical strings is **coercion**.
- **Vocabulary/labeling decisions.** Assigning the B2 label set and the exact `binding_role` vocabulary
  (`GROSS_EDGE`, …) to payload fields is a **normalization/labeling** act, not a structural pass-through.
- **Provenance canonicalization.** Producing **canonical unsigned-int epoch strings** for the provenance fields from
  whatever the payload carries is **coercion/defaulting**.
- **A non-payload dependency.** The producer/B3 require a **non-empty `cost_validity_contexts`** tuple. The Option-B
  payload carries **no** cost context; `opaque_cost_context` / Cell-3 is **deferred / gated**. Supplying it would be
  **defaulting/fabrication** of a gated input.

Every one of these is **B2 normalization / coercion / defaulting / schema repair** — exactly the work constraint 7
forbids smuggling into a new adapter, and exactly the responsibility B2 already owns. A boundary that performed them
would be a **second, parallel B2 normalizer in disguise** (normalization smuggling), violating the No-Touch Spine
Seal and the constitution's anti-fabrication rule.

**Therefore no payload-only Strict Translation Boundary is definable.** Per constraints 2 and 7, this charter
**records the blocker and STOPS** rather than defining one.

---

## 4. Classification of the Missing Work (separate, separately-gated)

The true missing edge is a **B2/pass-path ingestion-normalization contract decision**: how an Option-B reader
parsed payload is **ingested and normalized** into an exact `PublicRawSnapshotRecord` (the B2 raw carrier) — under
B2's existing canonical typing, label vocabulary, anti-coercion, and exact-string discipline — so that the existing
frozen chain (B2 normalizer → B3 → Producer → `PassiveShadowInput` → B4) can run unchanged. This decision:

- **belongs to B2 ingestion**, not to a thin translation adapter and not to S5;
- is **separate and separately gated** — it is **not** decided, designed, or authorized here;
- carries an **independent, also-gated dependency** on the **cost-context (Cell-3)** input the producer/B3 require,
  which remains **deferred**. Until Cell-3 (or an explicitly-chartered passive cost-context source) exists, even a
  correctly-normalized `PublicRawSnapshotRecord` cannot complete the pass path, because `cost_validity_contexts`
  cannot be supplied without fabrication.

**Two separate prerequisites** must each be chartered and ratified before the pass path is contract-complete: (a) a
**B2 ingestion-normalization** contract (parsed payload → exact `PublicRawSnapshotRecord`), and (b) a **passive
cost-context** source for `cost_validity_contexts` (Cell-3 or equivalent). Neither is opened here.

---

## 5. No-Touch Spine Seal (binding)

All existing modules and interfaces remain **frozen**. This charter proposes **no** parameter change, refactor,
widened accept, relaxed type gate, or behavior edit to the Reader, S2, B2 (`b2_normalization_contract` /
`b2_replay_normalization`), B3, Producer, Phase 5, B4, S4, S1, S5, or any existing lock test. The fix for the gap is
**a new, separate, ratified ingestion contract** — never a loosening of a frozen component to accept a raw payload.

---

## 6. Constraints That Bind Any Future Pass-Path Boundary (when/if it becomes definable)

These are recorded now so a future, properly-scoped boundary cannot drift:

- **Strict Translation Boundary discipline.** If — only after the §4 B2 ingestion-normalization decision — a thin
  pass-path edge is ever definable, it must be **standalone, stateless, deterministic, payload-only**, and must
  **NOT** compute edge, score, cost, intent, routing, actionability, identity, timestamps, or business semantics.
- **Identity Isolation.** The `S2IdentityWiringCandidate` must **bypass** any payload translation **untouched**: the
  boundary processes **payload only** and must **not** inspect, mint, hash, collapse, derive, stringify, route, or
  fall back on identity. Identity travels the S5 topology separately and intact.
- **Runner Exclusivity Ban.** The S5 runner **MUST NOT** implement this translation internally. A future S5 may only
  **invoke** a separately-ratified pass-path boundary; if that boundary is absent, the **S5 runtime must stop and
  report a blocker** (it must not inline normalization, and must not run a halt-only pipeline — §7).
- **No Normalization Smuggling.** No future "translation" may quietly absorb B2 normalization/coercion/defaulting/
  unit-math/schema-repair. The moment such work is required, it is a **B2/pass-path contract decision** (§4), not an
  adapter.

---

## 7. No Partial Runner (binding)

A halt-only or otherwise partial S5 runner runtime remains **UNAUTHORIZED**. **Both** the pass path **and** the halt
path must be **contract-complete** before any S5 runtime TDD slice is eligible. Because the pass-path edge is now
**formally blocked** (§3) pending the §4 decisions, **S5 runtime TDD remains ineligible**. The halt path being
contract-complete does **not** unlock a partial runner.

---

## 8. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 9. Precise State

- This charter **does not authorize S5 runtime**, **does not** make Phase 6.1 complete, and **does not** make Phase
  6.2 ready.
- It may make a **future B2/pass-path ingestion-normalization boundary eligible** to be chartered (§4) — but only as
  a **separate, separately-gated** decision; it authorizes **no** boundary, adapter, or runtime here.
- The **S1 durable storage medium** and the **real-cost Cell-3** assembly remain **separately gated** and
  **unbuilt/unbound**; the S1 sink stays a **test-only reference sink**.

---

## 10. Still-Forbidden Work

- **No** payload-only translation adapter from a parsed payload into the pass path (§3); **no** normalization/
  coercion/defaulting/unit-math/schema-repair adapter (§4); **no** fabricated `cost_validity_contexts`.
- **No** edit / widen / relax / refactor of the Reader, S2, B2, B3, Producer, Phase 5, B4, S4, S1, S5, or lock-tests
  (§5).
- **No** S5-internal translation; **no** S5 runtime (§6/§7); **no** halt-only / partial runner.
- **No** identity inspection/minting/derivation/stringify/fallback in any future boundary (§6).
- **No** Cell-3 assembly; **no** capacity activation.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Next Safe Step

- A **separately-authorized docs-only B2/pass-path ingestion-normalization contract charter** — deciding how an
  Option-B reader parsed payload is ingested and normalized into an exact `PublicRawSnapshotRecord` under B2's
  existing canonical typing/vocabulary/anti-coercion (no frozen-component edits), so the existing chain runs
  unchanged. **And, independently**, a **passive cost-context (Cell-3 or equivalent) source** charter for
  `cost_validity_contexts`. **Both** must be ratified before the pass path is contract-complete.
- Only **after both** prerequisites are ratified does an **S5 runtime TDD slice** (with both paths contract-complete)
  become eligible. The **S1 storage-medium** charter remains independently gated.
- **No implementation is authorized by this charter.**

**Conclusion:** evidence-first tracing of the frozen pass path (B4 ← `PassiveShadowInput` ← Producer ← B3 ← exact
`NormalizedEvidenceMaterial` ← B2 replay normalizer ← exact `PublicRawSnapshotRecord`; reader → raw `json.loads`
payload) shows the **earliest frozen input is an already-structured, exactly-typed B2 `PublicRawSnapshotRecord`**,
not a raw payload. Bridging an Option-B parsed payload to it would require **shape repair, type coercion,
vocabulary/labeling, provenance canonicalization, and a fabricated cost-context** — i.e. **B2 normalization plus a
gated Cell-3 dependency** — which constraint 7 forbids smuggling into a thin adapter. **No payload-only Strict
Translation Boundary is definable; this charter is a BLOCKER.** The missing work is classified as **two separate,
separately-gated decisions**: a **B2/pass-path ingestion-normalization** contract and a **passive cost-context
(Cell-3)** source. The **No-Touch Spine Seal**, **Runner Exclusivity Ban**, **Identity Isolation**, and **No Partial
Runner** all hold: existing modules stay **frozen**, S5 must **not** inline this work, and **S5 runtime TDD remains
ineligible** until **both** the pass and halt paths are contract-complete. This charter authorizes **no** boundary,
adapter, or runtime; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is
authorized.**
