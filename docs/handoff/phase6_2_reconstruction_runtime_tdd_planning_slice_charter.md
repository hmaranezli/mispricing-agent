# Phase 6.2 — Reconstruction Runtime TDD Planning & Slice Charter

> **This is a docs-only planning charter.** It plans the complete future Phase 6.2 reconstruction runtime as small,
> separately-authorized TDD slices. It **implements nothing and authorizes no executable slice**: no runtime code,
> no tests, no test execution, no DTO, no package, no loader, no state machine, no fixture, no Phase 6.1 edits, no
> S1-adapter edits, no Gate A/B edits, no frozen-component edits, no lock-test edits, no config, no pytest, no
> graphify, and no commit beyond this single docs file. It makes **no** Phase 6.2 runtime/paper/live/production
> readiness claim. It is subordinate to the full Phase 6.2 charter chain
> (`a9ed9f4`, `ef26f59`, `e9995e7`, `999a109`, `07135be`, `abd1b41`, `5dc757c`, `1071067`, `474cc6f`, `d7204d6`,
> `f57d116`, `44791ce`, `457d279`), the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises,
> those govern.

**Base:** `457d279b023ce4f400d71adeaefb596690736b6f`

---

## 1. Base / Purpose

**Base commit:** `457d279b023ce4f400d71adeaefb596690736b6f`.

Every Phase 6.2 design prerequisite is now ratified: risk inventory, source authority, lifecycle, artifact field
shape + correction, canonical encoding + digest, the classification predicate, and the precedence/atomicity
corrections (through `457d279`). This charter plans the **future** reconstruction runtime as a strict slice DAG with
RED→GREEN TDD discipline, maps every planned module/field/test to ratified evidence, and **audits testability under
the no-synthetic-S1-bypass rule**. It authorizes **no** executable slice; it names the single eligible next gate.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First Mapping

Re-read: the full Phase 6.2 chain (above) and the actual S1 runtime source. Every planned element maps to ratified
evidence:

- **S1 replay surface** — `phase6_1_s1_storage/s1_durable_sqlite_sink.py`: `replay()` returns append-ordered rows
  with columns `observation_kind, family_descriptor, artifact_locator, physical_record_position,
  provenance_timestamp, canonical_text_payload` (`append_sequence` omitted; `ORDER BY append_sequence`).
- **SCORE payload paths** — `phase6_1/b4_passive_scoring.py`: `family_payload.{passive_score_magnitude,
  score_basis_reference, score_inputs_summary=(source_venue, source_pair), score_unit_context,
  score_family_descriptor="passive_net_edge_diagnostic"}`; `observation_kind="SCORE"`; `provenance_timestamp=
  observed_at_epoch_ms`.
- **Phase 5 S1 decimal lexis** — `phase5/net_edge_calculator_boundary.py`: `_CANONICAL_DECIMAL=^-?\d+(\.\d+)?$`.
- **Artifact projection** — Gate A (`5dc757c`+`1071067`) logical shape; Gate B (`474cc6f`) canonical bytes + detached
  SHA-256.
- **Atomic step law** — `457d279` `Step(...)`, classify-all/apply-all, row-start snapshot, terminal relevance.

**Testability gate:** §8 audits whether every mandated test branch is constructible without violating the
no-synthetic-S1-bypass rule. A blocker is found and documented (§8); per §12, the next gate is the fixture/
testability charter — **no fixture exception is invented here**.

---

## 3. Isolated Package Boundary (planned, not created)

One future quarantined package **`phase6_2_shadow_intent/`** (analogous to the quarantined
`phase6_1_s1_storage/`):

- **No Phase 6.1 module may import it.** It may consume **caller-supplied S1 append-order replay rows read-only**.
- It **MUST NOT** modify `S5`, `S1`, `phase6_1/`, `phase6_1_s1_storage/`, the frozen DTOs, or any existing lock
  test. Dependency direction is strictly one-way: `phase6_2_shadow_intent/` reads S1 outputs; S1 / Phase 6.1 never
  know about it.

---

## 4. Planned Module Map & Dependency DAG (planned, not created)

| Module | Narrow ownership |
|---|---|
| `logical_model.py` | Gate A frozen/methodless logical definitions, predecessor `NoPredecessor\|PredecessorReference` option-sum, lifecycle slot/snapshot value types, and **closed structural validation** only. |
| `artifact_verifier.py` | Gate B **canonical-byte validation + detached SHA-256 verification**, **explicit** artifact reference, **one-read** frozen projection. **No writer / no artifact-authoring tool.** |
| `s1_evidence_projection.py` | **Exact whitelist-only** projection from caller-supplied S1 replay rows. **No** query DSL, SQLite writes, generic JSON walking, analytics, or identity invention. |
| `classification_predicates.py` | **Pure** context, timestamp, expiry, unit, decimal, and crossing classifiers. **No state mutation.** |
| `atomic_replay_step.py` | The exact `457d279` `Step` law, duplicate-root guard, row-start snapshot, classify-all/apply-all, dual-snapshot atomic result. |
| `reconstruction.py` | **Minimal append-order fold** over the verified artifact projection + ordered S1 rows. **No** sorting, filtering, parallelism, persistence, export, reporting, or live source. |

**One-way dependency DAG (no cycles, no shared mutable state):**

```
logical_model            (leaf — no intra-package deps)
s1_evidence_projection   (leaf — no intra-package deps)
artifact_verifier        → logical_model
classification_predicates→ logical_model, s1_evidence_projection
atomic_replay_step       → classification_predicates, logical_model, s1_evidence_projection
reconstruction           → atomic_replay_step, artifact_verifier, s1_evidence_projection, logical_model
```

**Circular imports and shared mutable state are forbidden.** All state is caller-owned, replay-local,
instance-scoped (§10).

---

## 5. Mandatory Slice DAG (each a separate future human-authorized TDD slice + commit)

| Slice | Scope | Depends on | Excludes |
|---|---|---|---|
| **A — Logical Model** | frozen exact types/constructors + structural validation (`logical_model.py`) | — | bytes, digest, file I/O, S1 parsing, predicates, replay |
| **B — Artifact Verification** | canonical JSON bytes + detached digest + immutable projection (`artifact_verifier.py`); **explicit locator only** (no latest/glob/env/default/sidecar) | A | S1, replay |
| **C — S1 Evidence Projection** | exact replay-row + canonical payload paths; row/payload consistency + Phase 5 lexical contract (`s1_evidence_projection.py`) | — (leaf) | lifecycle decisions |
| **D — Classification Predicates** | pure classifiers over already-validated logical inputs (`classification_predicates.py`) | A, C | slot/container mutation |
| **E — Atomic Replay Step** | `Step(RowStartShadowSnapshot, RowStartSeenTargetPairs, CurrentS1Row, FrozenManifestProjection)`; classify-all/apply-all + deterministic `HardFailure` (`atomic_replay_step.py`) | D | replay loop, persistence |
| **F — Reconstruction Fold** | minimal sequential fold over append-ordered S1 replay (`reconstruction.py`) | B, E | alternate input source, query surface, analytics, export |
| **G — Runtime Closeout Ratification** | integration/lock tests + exact scope closeout only | A–F | any new behavior |

**No slice may absorb another slice silently.** Slice ordering respects the DAG (A→B; C; D needs A+C; E needs D; F
needs B+E; G last).

---

## 6. TDD Discipline (per slice, binding)

For **every** slice: pin **exact RED tests first**; **minimal GREEN implementation second**; run **focused tests +
the relevant frozen regression suite** (package locks, S1/S5 peers as applicable); **STOP and report after that
single slice**; **no opportunistic refactor or adjacent implementation**; and **no Phase 6.2 completion claim before
Slice G ratification**. Each slice is its own human-authorized "Begin…" task and its own commit.

---

## 7. Mandatory Behavioral Test Matrix (planned → slice)

| Behavior | Slice(s) |
|---|---|
| directional positive / negative crossing; `INERT_STATE` no-crossing | D, E, F |
| root establishment + same-row exclusion | E, F |
| permanent root unit-mismatch non-establishment (frozen `AUDIT_REPLAYED`) | E, F |
| duplicate targeted pair **before** terminal handling (HardFailure) | E, F |
| dormant definitions (no intent, no error) | F |
| context inequality no-op | D, E, F |
| malformed-context **relevance scoping** (only fails when an established non-terminal slot needs it) | D, E, F |
| **row/payload family + timestamp consistency** (agreement accepted; **disagreement → HardFailure**) | C, E — **see §8 blocker** |
| negative delta; zero duration; inclusive window boundary (`0 ≤ delta ≤ duration`); expiry precedence | D, E |
| separate S1 (`^-?\d+(\.\d+)?$`) vs Gate B decimal grammars | B, C, D |
| `INTENT_RETIRED` unreachable (never synthesized) | D, E, F |
| open/frozen EOF validity (≤1 terminal) | F |
| multi-intent classify-all/apply-all | E, F |
| iteration-order independence | E, F |
| `HardFailure` publishes no snapshot | E, F |
| `SeenTargetPairs` + shadow snapshot commit together | E, F |
| repeated whole-replay determinism / idempotency | F, G |
| no mutation / write-back / global state | C, D, E, F, G |

---

## 8. Test-Evidence Boundary & Fixture Audit (binding)

**Rule:** successful reconstruction/integration tests **MUST** use **temporary SQLite S1 audit fixtures populated
through the ratified S1 adapter** (`S1DurableSqliteSink.record_observation`). **Hand-rolled successful S1
records/rows and direct intent-state fabrication are FORBIDDEN.** Artifact-verifier negative tests **may** use
malformed artifact bytes (rejection of untrusted bytes is that boundary's direct responsibility) — Slice B negatives
are unblocked.

**Audit finding (BLOCKER — proven from source):** `S1DurableSqliteSink.record_observation` derives **every**
persisted column **and** the `canonical_text_payload` from the **same `record`** — `observation_kind` (column) and
the projected payload `observation_kind` share `record.observation_kind`; the `family_descriptor` column
(`_family_descriptor(record.family_payload)` = `family_payload["score_family_descriptor"]`) and the projected payload
`score_family_descriptor` share one source; the `provenance_timestamp` column (`_opaque_text(record.provenance_
timestamp)`) and the projected payload timestamp share one source. **Therefore the adapter structurally GUARANTEES
row↔payload internal consistency.**

Consequences for the mandated matrix:

- **Constructible through the adapter** (record a valid record via the genuine pipeline): all positive lifecycle
  behaviors; dormant; context inequality; duplicate targeted pair (two records with identical Silver pair); HALT /
  non-SCORE; multi-intent; determinism/idempotency; and the **agreement** (positive) side of row/payload
  consistency.
- **NOT constructible through the adapter without a forbidden synthetic bypass** — the **row/payload DISAGREEMENT →
  `HardFailure`** negative branches (`f57d116` §5 family-kind/descriptor agreement; §6 timestamp row-text ==
  payload-integer): the adapter can never emit a row whose column disagrees with its embedded payload, so testing
  that defensive branch would require **direct SQL corruption, a fake `sqlite3.Row`, monkeypatched row fabrication,
  or adapter bypass** — all **FORBIDDEN** here.
- The broader class of **malformed-payload-content** negative branches (e.g. not-exactly-two-text
  `score_inputs_summary`, non-canonical S1 magnitude lexis, negative/non-integer `provenance_timestamp`) requires
  recording a deliberately-malformed, non-pipeline record — whose admissibility is itself the controlled-negative-
  fixture question, **not** resolved here.

**Resolution (per the rule):** these negative branches require a **controlled negative-fixture exception**, which
**MUST NOT** be invented in this charter. A separate **docs-only human-authorized fixture-boundary charter** is
**named as the blocker** (§12). The positive-evidence and adapter-constructible branches remain testable through the
ratified adapter and are **not** blocked; the **disagreement/malformed negative branches** are.

---

## 9. Failure Model (binding)

- **`HardFailure` is distinct** from a lifecycle state, an S4 HALT, and an unexpected programmer exception.
- **Deterministic failure precedence, independent of map/iteration order** (same fixed inputs ⇒ same failure
  outcome).
- **Never silently return `RowStartShadowSnapshot` on failure**; **never expose partial proposals** (`457d279` §3–§5).
- **No actionability / error-recovery / retry semantics are invented** here; concrete error-aggregation/exception
  types are **deferred** to the slice charters, preserving deterministic failure reporting.

---

## 10. Runtime Purity (binding)

- **Caller-owned, replay-local, instance-scoped state only.**
- **No** threads, async workers, multiprocessing, scheduler, timer, wall clock, network, broker/exchange/API, cache,
  singleton, module-level mutable state, database writes, telemetry aggregation, wallet, balance, PnL, portfolio,
  capacity, or emission surface.
- **Capacity remains deferred at exactly 0 emit sites.** Phase 6.1 stays frozen, COMPLETE + RATIFIED.

---

## 11. Completion Criteria / Reporting (this charter delivers)

- **Future package/module map** (§4); **dependency DAG** (§4); **slice A–G table** (§5); **RED/GREEN + regression
  requirements per slice** (§6); **behavioral test matrix → slice** (§7); **testability/fixture blockers** (§8);
  **failure-taxonomy boundary** (§9); **frozen files/packages** (below); **first eligible executable slice / gate**
  (§12).
- **Frozen / untouched:** `phase6_1/` (all modules), `phase6_1_s1_storage/`, the frozen DTOs
  (`ObservationScoreRecord` / `ObservationHaltRecord` / `S2IdentityWiringCandidate` / `NetEdgeCalculationResult` /
  `PassiveShadowInput` / cost carriers), `S5`, every lock test, `config.py`, and the Gate A/B artifact charters.
  The future package adds only new files under `phase6_2_shadow_intent/` and its own tests.

---

## 12. Next Gate (ratified)

- **`457d279` did NOT make a runtime slice eligible on its own**; the testability audit (§8) had to be performed
  first, and it **found a blocker**.
- **A fixture/testability BLOCKER exists** (the row/payload-disagreement and malformed-evidence negative branches
  are not constructible through the ratified adapter without a forbidden synthetic bypass). **Per the rule, the
  ONLY next eligible gate is a separately-authorized docs-only "Phase 6.2 Negative-Evidence Fixture-Boundary
  Charter"** — which must decide, under human authorization, whether and how a **controlled negative-fixture
  exception** (and only that) is permitted for the unconstructible negative branches, **without** weakening the
  no-synthetic-S1-bypass rule for successful evidence.
- **Slice A (Logical Model) and Slice B (Artifact Verification) are themselves free of the S1 fixture blocker**
  (Slice A has no S1 dependency; Slice B uses malformed artifact bytes, which is permitted), but **because an
  unresolved fixture/testability blocker exists in the mandated matrix, this charter names ONLY the fixture-boundary
  charter as the next gate** (not Slice A), per the governing constraint.
- **This charter does NOT open, draft, implement, or authorize the fixture-boundary charter or any slice.** **Phase
  6.2 remains UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0 emit
  sites); production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** the future Phase 6.2 reconstruction runtime is planned (docs-only) as the quarantined package
**`phase6_2_shadow_intent/`** with six narrowly-owned modules — `logical_model`, `artifact_verifier`,
`s1_evidence_projection`, `classification_predicates`, `atomic_replay_step`, `reconstruction` — under a **one-way,
acyclic dependency DAG** (no shared mutable state), built as **seven sequential, separately-authorized RED→GREEN TDD
slices A–G** (Logical Model → Artifact Verification → S1 Evidence Projection → Classification Predicates → Atomic
Replay Step → Reconstruction Fold → Runtime Closeout Ratification), **no slice absorbing another**, each its own
"Begin…" task + commit + STOP, with the full behavioral test matrix mapped to slices. The **test-evidence boundary**
requires successful fixtures **through the ratified S1 adapter** (no hand-rolled successful records, no intent-state
fabrication), permits **malformed artifact bytes** for the verifier, and the **fixture audit proves a BLOCKER**: the
ratified `record_observation` derives every row column **and** the canonical payload from one `record`, structurally
guaranteeing row↔payload consistency, so the **row/payload-disagreement → `HardFailure`** and malformed-evidence
negative branches are **not constructible without a forbidden synthetic bypass** (direct SQL / fake `sqlite3.Row` /
monkeypatch / adapter bypass). **`HardFailure`** stays distinct from lifecycle state / S4 HALT / programmer
exceptions, with **deterministic order-independent failure precedence**, **no partial-snapshot exposure**, and **no
invented recovery/retry**. Runtime purity bans threads/async/clock/network/broker/cache/singleton/global/DB-write/
telemetry/wallet/PnL/capacity/emission; **capacity stays deferred at 0 emit sites**; the frozen `phase6_1/`,
`phase6_1_s1_storage/`, DTOs, `S5`, lock tests, `config.py`, and Gate A/B charters stay **untouched**. Because an
**unresolved fixture/testability blocker exists**, the **only** next eligible gate is the separately-authorized
docs-only **"Phase 6.2 Negative-Evidence Fixture-Boundary Charter"** — **not** Slice A — **not opened here**. **Phase
6.2 remains UNBUILT and NOT runtime-ready. No executable work is authorized.**
