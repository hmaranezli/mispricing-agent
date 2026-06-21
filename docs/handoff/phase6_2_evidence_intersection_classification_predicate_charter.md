# Phase 6.2 — Evidence-Intersection Classification Predicate Charter

> **This is a docs-only predicate charter.** It pins the **exact, bounded, non-actionable recognition predicates**
> that classify the lifecycle trigger classes over
> `ShadowState = Replay(FrozenProjection(SealedScenarioDefinitionArtifact), OrderedS1AuditRecords)`. It **implements
> nothing and authorizes nothing executable**: no runtime code, no tests, no test execution, no DTO, no loader, no
> state machine, no lock-test edits, no frozen-component edits, no Phase 6.1 edits, no S1-adapter edits, no Gate A/B
> edits, no Phase 6.2 runtime, no pytest, no graphify. It makes **no** Phase 6.2 runtime/paper/live/production
> readiness claim. It is subordinate to
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_canonical_encoding_digest_charter.md`,
> `docs/handoff/phase6_2_gate_a_predecessor_option_sum_targeted_correction_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_field_shape_charter.md`,
> `docs/handoff/phase6_2_source_authority_determinism_targeted_amendment_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_source_boundary_charter.md`,
> `docs/handoff/phase6_2_multi_event_context_supply_shadow_state_boundary_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_lifecycle_state_transition_charter.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `474cc6fb46c48674c582f12756f33523d225b85f`

---

## 1. Base / Purpose

**Base commit:** `474cc6fb46c48674c582f12756f33523d225b85f`.

Every prior gate is ratified: the lifecycle table (`e9995e7`, terminal-corrected by `999a109`), the source boundary
(`07135be`) + amendment (`abd1b41`), and the artifact Gate A field-shape (`5dc757c` + `1071067`) and Gate B
canonical-encoding/digest (`474cc6f`). This charter pins the **last open design item**: the exact recognition
**predicate** for each lifecycle trigger class — the bounded passive classifiers that read **only** whitelisted S1
canonical evidence and the verified frozen artifact projection, and emit **only** a closed lifecycle trigger class.
It builds no runtime; it fixes the predicate contract.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First Path Proof (every S1 path proven from ratified source)

Re-read: `e9995e7`, `999a109`, `07135be`, `abd1b41`, `5dc757c`, `1071067`, `474cc6f`. Each S1 path is proven from
ratified runtime source — **none absent or ambiguous**, so this charter is created (the §2 STOP is not triggered):

- **S1 replay row columns** — `phase6_1_s1_storage/s1_durable_sqlite_sink.py` DDL + replay `SELECT`:
  `observation_kind`, `family_descriptor`, `artifact_locator`, `physical_record_position`, `provenance_timestamp`,
  `canonical_text_payload` (proven present; `append_sequence` omitted, `b06d7ed` §6).
- **SCORE family payload** — `phase6_1/b4_passive_scoring.py` (`build_passive_observation_record`):
  `family_payload = {"passive_score_magnitude": result.net_edge_value, "score_basis_reference": result,
  "score_inputs_summary": (pass_handoff.source_venue, pass_handoff.source_pair),
  "score_unit_context": result.net_edge_unit, "score_family_descriptor": _FAMILY_DESCRIPTOR}`;
  `observation_kind="SCORE"`; `provenance_timestamp = pass_handoff.observed_at_epoch_ms` (exact non-negative `int`).
- **`score_inputs_summary` shape** — proven as **exactly two ordered scalars** `(source_venue, source_pair)`, each a
  **non-empty, non-whitespace `str`** (validated by `phase6_1/passive_shadow_input.py` `_require_str_field`).
- **`passive_score_magnitude` / `score_unit_context`** — proven as the Phase-5 `net_edge_value` (signed canonical
  decimal string) and `net_edge_unit` (unit token string) of `NetEdgeCalculationResult`
  (`phase5/net_edge_calculator_boundary.py`).
- **Durable `provenance_timestamp`** — written as `_opaque_text(record.provenance_timestamp)`; for a SCORE this is
  the decimal text of the epoch-ms `int`; for a HALT it is `NULL` (`s4_halt_materialization.py` sets it `None`).
- **Artifact projection fields** — Gate A/B verified: `exposure_orientation`, `passive_boundary_magnitude`,
  `boundary_unit_context`, `hypothetical_window_duration_ms`.

---

## 3. Closed Field Whitelist (binding)

Predicates may read **only** these fields. **All unlisted fields, generic dict/JSON scraping, key-name guessing,
fuzzy/recursive walking, and reading any non-whitelisted payload member are BANNED.**

- **S1 replay row (columns):** `observation_kind`, `family_descriptor`, `artifact_locator`,
  `physical_record_position`, `provenance_timestamp`, `canonical_text_payload`.
- **SCORE payload only** (read at exact canonical paths inside `canonical_text_payload` → `family_payload`):
  `family_payload.passive_score_magnitude`, `family_payload.score_unit_context`,
  `family_payload.score_inputs_summary` (a 2-element ordered list `[source_venue, source_pair]`),
  `family_payload.score_family_descriptor`.
- **Artifact projection only** (Gate A/B verified frozen projection): `exposure_orientation`,
  `passive_boundary_magnitude`, `boundary_unit_context`, `hypothetical_window_duration_ms`.

`score_basis_reference`, `opaque_cost_context`, HALT payload internals, and every other field are **out of scope**
and never read. Historical S1 evidence is consumed **verbatim and opaque**, never censored/normalized/rewritten.

---

## 4. Intent Establishment (binding)

- **`EVIDENCE_INTERSECTION` begins with exact opaque equality** of the manifest definition's Silver pair and the S1
  record's `(artifact_locator, physical_record_position)` — both components compared as **opaque text, byte-exact**,
  never coerced/parsed (the position is never read as an integer, `b06d7ed` §6).
- **Only an exact qualifying SCORE may establish `AUDIT_REPLAYED → INTENT_RECORDED`** (edge 1 of `e9995e7` §4). A
  qualifying SCORE is the targeted record with `observation_kind == "SCORE"` carrying well-formed whitelisted SCORE
  evidence (`passive_score_magnitude`, `score_unit_context`, the 2-scalar `score_inputs_summary`, and a well-formed
  `provenance_timestamp`); **for a directional definition** it must additionally be **unit-comparable**
  (`score_unit_context` exactly equals the artifact `boundary_unit_context`).
- **The establishing SCORE supplies the immutable root context and anchor timestamp**: the root
  `score_inputs_summary` `(source_venue, source_pair)` (§5) and the anchor `provenance_timestamp` (§8). These are
  captured once and never mutated.
- **A unit mismatch for a directional definition is passive not-comparable: no transition** (the intent stays
  `AUDIT_REPLAYED`, awaiting a unit-comparable qualifying SCORE; not fail-fast, not a halt).
- **A targeted HALT / non-SCORE / missing / malformed SCORE** (a record at the manifest Silver pair that is not a
  well-formed qualifying SCORE) **is an encounter-time hard fail-fast** (§10) — never an S4 halt, never a synthetic
  intent.
- **One definition creates at most one lifecycle slot**; once `INTENT_RECORDED` is reached, re-encountering the
  establishing key (idempotent replay) **never** creates a duplicate intent. The `AUDIT_REPLAYED → INTENT_RECORDED`
  edge fires at most once per slot.

---

## 5. Multi-Event Context Boundary (binding)

- The root `family_payload.score_inputs_summary` is pinned as **exactly two ordered, non-empty text scalars**:
  **`source_venue` then `source_pair`** (index 0, then index 1) — proven in §2.
- **A later SCORE is comparable to that intent only when its two `score_inputs_summary` values are exactly equal to
  the root values** (`later.source_venue == root.source_venue` **and** `later.source_pair == root.source_pair`), by
  **exact opaque text equality**.
- **No** normalization, aliasing, case-folding, venue/pair inference, or cross-context comparison.
- **This context equality is classification only; it MUST NOT become intent identity or replace the Silver-pair
  key** (the Silver pair establishes the root slot, §4; context equality only selects which **later** observations
  the established intent tracks).
- **Context inequality is an irrelevant no-op** (self-loop; no transition).

Established intents are tracked across later events **only** through this context equality — never by re-matching the
Silver pair (later records have distinct positions) and never by any global registry (§10).

---

## 6. Exact Arithmetic and Units (binding)

- Parse the audited `passive_score_magnitude` and the artifact `passive_boundary_magnitude` with **exact decimal
  arithmetic only** (exact base-10 from the canonical decimal strings of `5dc757c` §8 / `474cc6f` §11).
- **Ban** native binary float / double, rounding, quantization, coercion, NaN, infinity, locale parsing, and
  **sign-derived orientation** (orientation is declared, never inferred from the magnitude's sign).
- **Directional unit equality must be exact** (`score_unit_context` vs `boundary_unit_context`, opaque-token byte
  equality; no normalization/conversion/FX/case-fold/alias).
- **Unit inequality is passive not-comparable and causes no transition** (no-op; not fail-fast, not a halt).

---

## 7. Directional Predicate (`PASSIVE_EVIDENCE_CROSSING`) (binding)

For a unit-comparable, context-comparable later SCORE inside the window (§8), with exact decimal `evidence =
passive_score_magnitude` and `boundary = passive_boundary_magnitude`:

| Declared `exposure_orientation` | Crossing condition |
|---|---|
| `POSITIVE_EXPOSURE` | `evidence >= boundary` |
| `NEGATIVE_EXPOSURE` | `evidence <= boundary` |
| `INERT_STATE` | **no `PASSIVE_EVIDENCE_CROSSING` exists** (inert carries no boundary/unit; no crossing is ever defined) |

- **A crossing may produce ONLY `INTENT_RECORDED → HYPOTHETICAL_CONDITION_MET`** (edge 3). Once in
  `HYPOTHETICAL_CONDITION_MET`, a further satisfied crossing is **sustaining/irrelevant → no-op self-loop** (edge 9);
  there is **no** backward edge and **no** second crossing transition.
- **The establishing/root observation cannot perform two transitions**: crossing evaluation begins **only** with
  **strictly later append-ordered** comparable observations — the root record itself is never re-evaluated for
  crossing or expiry.
- A non-satisfied crossing (inside window, unit- and context-comparable) is a **no-op self-loop**.

---

## 8. Timestamp Predicate (`TIMESTAMP_DELTA`) (binding)

- **Anchor** = the establishing SCORE `provenance_timestamp`. **Comparison** = a later append-ordered, comparable
  SCORE `provenance_timestamp`. **Duration** = the artifact `hypothetical_window_duration_ms`.
- All three are **exact non-negative integer milliseconds** (the durable `provenance_timestamp` text parsed as an
  exact non-negative integer; the duration per `474cc6f` §12). **Append order is authoritative; timestamps need NOT
  be monotonic** (`abd1b41` §9).
- `delta = comparison_timestamp - anchor_timestamp` (exact integer arithmetic):

| `delta` | Classification |
|---|---|
| `delta < 0` | **passive timestamp non-comparability** — no transition, and **never** expiry (no-op self-loop) |
| `0 <= delta <= duration` | **inside the hypothetical window** — proceed to the §7 crossing predicate (directional) or no-op (inert) |
| `delta > duration` | **classify `INTENT_EXPIRED`** |

- **Expiry takes precedence over crossing** on an observation beyond the window: if `delta > duration`, the record
  classifies `INTENT_EXPIRED` (edge 4 from `INTENT_RECORDED`, edge 7 from `HYPOTHETICAL_CONDITION_MET`) and the
  crossing predicate is **not** evaluated for that record.
- **No** wall clock, `now()`, timer, scheduler, polling, EOF expiry, or fabricated terminal. A negative or
  out-of-order delta **never** silently produces expiry.

---

## 9. Lifecycle Closure (binding)

- **Every legal edge and absorbing-terminal rule of `e9995e7` §4 (terminal-corrected by `999a109` §2) is
  preserved.** The closed state set is `{AUDIT_REPLAYED (initial), INTENT_RECORDED, HYPOTHETICAL_CONDITION_MET,
  INTENT_EXPIRED (absorbing), INTENT_RETIRED (absorbing)}`; the only legal forward path is `AUDIT_REPLAYED →
  INTENT_RECORDED → (HYPOTHETICAL_CONDITION_MET)? → (INTENT_EXPIRED | INTENT_RETIRED)` plus no-op self-loops; every
  unlisted edge is forbidden; **at most one terminal per intent**; **open frozen non-terminal state at replay EOF is
  valid audit state**.
- **`INTENT_RETIRED` has NO currently provable S1 recognition predicate.** The whitelisted evidence (§3) contains
  no "passive close-out / retirement" signal. It is therefore pinned **reserved but UNREACHABLE from the current
  evidence vocabulary** — edges 5 (`INTENT_RECORDED → INTENT_RETIRED`) and 8 (`HYPOTHETICAL_CONDITION_MET →
  INTENT_RETIRED`) have **no firing predicate** and never fire under this charter.
- **`INTENT_RETIRED` is NEVER synthesized** from replay EOF, irrelevance, HALT, malformed evidence, unit mismatch,
  or condition completion. (The only reachable terminal under the current evidence vocabulary is `INTENT_EXPIRED`;
  otherwise an intent stays open/frozen — valid audit state.)
- **The equality-only degraded fallback (`07135be` §13 / `abd1b41` §10) remains UNACTIVATED** — this charter pins
  the full directional + expiry predicates over the verified artifact projection and does not invoke the
  contingency.

---

## 10. Error & Side-Effect Firewall (binding)

- **Malformed canonical evidence required for a classification is a Phase 6.2 hard fail-fast** — never an S4 halt.
  ("Required" = the specific whitelisted field consumed by the predicate being evaluated: the
  `provenance_timestamp` for `TIMESTAMP_DELTA`; additionally `passive_score_magnitude` + `score_unit_context` for an
  inside-window directional crossing; the 2-scalar `score_inputs_summary` for context comparison.) A **targeted**
  HALT / non-SCORE / missing / malformed SCORE at the establishing key is likewise hard fail-fast (§4).
- **HALT, irrelevant, non-comparable, and unit-mismatch records are passive no-ops** (not errors, not fail-fast, not
  halts) — they leave state unchanged.
- **No mutation / write-back** to S1, S5, Phase 6.1, the Gate A/B artifacts, or any frozen DTO. **No** global
  registry / cache / singleton / module-level mutable state (shadow state is caller-owned, instance-scoped,
  reconstructible from the fixed inputs — `07135be` §8 / `999a109` §3).
- **No** actionability, advice, ranking, realized PnL, capacity, or broker / exchange / paper / live / execution /
  routing integration. **Capacity remains DEFERRED at exactly 0 emit sites.**
- Unexpected programmer/runtime errors remain **fail-fast** and are never swallowed or converted into a passive
  classification (`abd1b41` §6 / `061bf1b` §7).

---

## 11. Consolidated Predicate Truth Table (binding)

For an **established** intent with root context `(venue₀, pair₀)`, anchor `T₀`, and definition variant, evaluating a
**strictly later append-ordered** S1 record `R` (current state ∈ {`INTENT_RECORDED`, `HYPOTHETICAL_CONDITION_MET`}):

| `R` shape / relation | Directional intent | Inert intent |
|---|---|---|
| `R` not SCORE (HALT/non-SCORE, not targeted) | no-op self-loop | no-op self-loop |
| `R` SCORE, context ≠ `(venue₀,pair₀)` | irrelevant no-op | irrelevant no-op |
| `R` SCORE, context =, `provenance_timestamp` malformed | **hard fail-fast** | **hard fail-fast** |
| `R` SCORE, context =, `delta < 0` | non-comparable no-op | non-comparable no-op |
| `R` SCORE, context =, `delta > duration` | **`INTENT_EXPIRED`** (expiry precedence) | **`INTENT_EXPIRED`** |
| `R` SCORE, context =, `0≤delta≤duration`, unit ≠ | not-comparable no-op | (no unit) no-op |
| `R` SCORE, context =, `0≤delta≤duration`, unit =, magnitude malformed | **hard fail-fast** | n/a |
| `R` SCORE, context =, in-window, unit =, crossing holds, state `INTENT_RECORDED` | **`HYPOTHETICAL_CONDITION_MET`** | n/a (no crossing) |
| `R` SCORE, context =, in-window, unit =, crossing holds, state `HYPOTHETICAL_CONDITION_MET` | sustaining no-op | n/a |
| `R` SCORE, context =, in-window, unit =, crossing not held | no-op self-loop | no-op self-loop |

Absorbing terminals (`INTENT_EXPIRED`, `INTENT_RETIRED`): any later `R` → absorbing self-loop no-op. Establishment
(`AUDIT_REPLAYED → INTENT_RECORDED`) is per §4. `INTENT_RETIRED` is unreachable (§9).

---

## 12. Status & Next Safe Gate (ratified)

- **Phase 6.2 remains UNBUILT and NOT runtime-ready. This charter authorizes no executable work.**
- **Phase 6.1:** frozen, COMPLETE + RATIFIED. **Capacity:** deferred (0 emit sites). **Production / live / paper /
  canary / execution / routing / actionability:** forbidden.
- With every Phase 6.2 design prerequisite (`a9ed9f4` §9 inventory; source authority; lifecycle; artifact field
  shape + encoding/digest; and now the **classification predicate**) pinned, a **separately-authorized Phase 6.2
  shadow-intent reconstruction runtime / verifier / state-machine / container TDD slice** becomes the **eligible
  next gate** — **but this charter does NOT open, draft, or perform it**, and a frozen-component / lock-touching
  slice would require its own human authorization under `CLAUDE.md`.

**Conclusion:** the Phase 6.2 evidence-intersection classification predicates are pinned (docs-only) over
`ShadowState = Replay(FrozenProjection(SealedScenarioDefinitionArtifact), OrderedS1AuditRecords)`, reading **only**
the closed whitelist — S1 row `{observation_kind, family_descriptor, artifact_locator, physical_record_position,
provenance_timestamp, canonical_text_payload}`, SCORE `{passive_score_magnitude, score_unit_context,
score_inputs_summary, score_family_descriptor}`, and artifact `{exposure_orientation, passive_boundary_magnitude,
boundary_unit_context, hypothetical_window_duration_ms}` (all generic scraping and unlisted fields banned).
**Establishment** (`AUDIT_REPLAYED → INTENT_RECORDED`) requires an exact opaque Silver-pair `EVIDENCE_INTERSECTION`
plus a qualifying (and, for directional, unit-comparable) SCORE that supplies the immutable root context
`(source_venue, source_pair)` and anchor timestamp; a directional unit mismatch is a passive no-op, a targeted
HALT/non-SCORE/missing/malformed SCORE is hard fail-fast, and one definition yields at most one slot.
**Context equality** (later `source_venue` **and** `source_pair` exactly equal to the root, no normalization) is
classification only — never identity, never replacing the Silver key — and inequality is an irrelevant no-op.
**Exact decimal** arithmetic governs `PASSIVE_EVIDENCE_CROSSING` (`POSITIVE_EXPOSURE`: evidence ≥ boundary;
`NEGATIVE_EXPOSURE`: evidence ≤ boundary; `INERT_STATE`: no crossing), which may only fire `INTENT_RECORDED →
HYPOTHETICAL_CONDITION_MET` on a strictly-later comparable observation (never the root, never twice). **`TIMESTAMP_
DELTA`** (`delta = comparison − anchor`, exact integers, append order authoritative, non-monotonic) classifies
`delta < 0` as non-comparable (never expiry), `0 ≤ delta ≤ duration` as in-window, and `delta > duration` as
**`INTENT_EXPIRED`**, with **expiry taking precedence over crossing** and **no wall-clock / timer / scheduler / poll
/ EOF / fabricated terminal**. The full `e9995e7`/`999a109` lifecycle (legal edges, absorbing terminals, at-most-one
terminal, open-frozen-EOF valid) is preserved; **`INTENT_RETIRED` is reserved but UNREACHABLE** (no S1 retirement
vocabulary) and never synthesized; the **equality-only fallback stays unactivated**. Malformed required evidence is
a **Phase 6.2 hard fail-fast (never an S4 halt)**; there is **no** mutation/write-back, **no** global
registry/cache/singleton, **no** actionability/PnL/ranking/capacity/integration, and **capacity stays deferred at 0
emit sites**. **Phase 6.1 stays frozen, COMPLETE + RATIFIED; Phase 6.2 remains UNBUILT and NOT runtime-ready**; the
eligible next gate — a separately-authorized reconstruction runtime/state-machine/container TDD slice — is **not
opened here**. **No executable work is authorized.**
