# Phase 6.2 — Negative-Evidence Fixture-Boundary Charter

> **This is a docs-only fixture-boundary authorization charter.** It authorizes **only** a quarantined, tests-only
> mechanism for constructing **intentionally invalid** S1 replay-row inputs that **MUST be rejected** with
> `HardFailure` — so the Phase 6.2 rejection branches that the ratified S1 adapter cannot emit become testable
> **without** weakening the no-synthetic-S1-bypass rule for successful evidence. It **implements nothing**: no
> runtime, no tests, no fixture code, no package, no DTO, no adapter, no database file, no schema, no lock-test, no
> Phase 6.1 edits, no S1-storage edits, no Gate A/B edits, no config, no pytest, no graphify. It is exactly one docs
> file. It makes **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_reconstruction_runtime_tdd_planning_slice_charter.md` and the full Phase 6.2 chain
> (`…predicate…`, `…f57d116…`, `…44791ce…`, `…457d279…`, the Gate A/B charters), the S1 durable-storage charters,
> and `CLAUDE.md`; where any conflict arises, those govern **except** for the single, explicitly-mapped supersession
> in §3.

**Base:** `52116525be48f22feb2c700931067f67addd8bb9`

---

## 1. Base / Purpose

**Base commit:** `52116525be48f22feb2c700931067f67addd8bb9`.

`5211652` (planning) correctly identified a **blocker**: the ratified `S1DurableSqliteSink.record_observation`
derives **every** persisted column **and** the `canonical_text_payload` from the **same** `record`, so it
**structurally guarantees row↔payload consistency** — the Phase 6.2 defensive rejection branches (row/payload
disagreement, malformed-evidence) are **not constructible through the adapter** without a forbidden synthetic
bypass. This charter closes **only** that blocker by authorizing **one** narrow, quarantined, tests-only
negative-evidence mechanism, fully isolated from successful-evidence authority. It implements nothing.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First Clause Inspection (quoted; isolation confirmed)

**Preserved no-synthetic-SUCCESSFUL-evidence clauses (NOT weakened):**

- `5211652` §8: "Hand-rolled **successful** S1 records/rows and direct intent-state fabrication are **FORBIDDEN**";
  "successful reconstruction/integration tests **MUST** use temporary SQLite S1 audit fixtures populated **through
  the ratified S1 adapter**."
- `ef26f59` §5: "**ad-hoc synthetic bypasses of S1** — hand-rolled intents that never flowed through the S1
  boundary — are **forbidden**."
- `999a109` §9: "**ad-hoc synthetic bypasses of S1** — hand-rolled intents/records that never flowed through the S1
  boundary, or reading from a non-S1 side channel — are **forbidden**."
- `abd1b41` §7: "synthetic observed-event bypass remains **forbidden**."

**Narrowly-affected clause (the only one superseded, §3):**

- `5211652` §8: "testing that defensive branch would require **direct SQL corruption, a fake `sqlite3.Row`,
  monkeypatched row fabrication, or adapter bypass** — all **FORBIDDEN** here."

**Isolation confirmation (the §2 STOP condition is NOT triggered):** the exception authorizes **only**
intentionally-invalid rows whose **sole** permitted outcome is `HardFailure` (§8 poison invariant); it grants **no**
observed-evidence authority and **no** successful-reconstruction authority; the fixture is **physically isolated**
(`tests/fixtures/`, never imported by production, §4) and processed by the **same production rejection path** (§13).
The exception is therefore **cleanly separable** from successful evidence — successful evidence stays **100%
adapter-only** (§10). Because isolation holds, this charter is created.

---

## 3. Narrow Supersession (binding)

**Preserved (absolute):** the ban on **synthetic SUCCESSFUL** S1 evidence, **successful** shadow transitions,
**fabricated intent state**, and **alternate observed-event sources** stands in full force, everywhere.

**Added — exactly one exception:** *intentionally invalid, **tests-only** raw replay-row fixtures may be supplied
**solely** to prove that Phase 6.2 rejects malformed evidence with `HardFailure`.* This exception:

- grants **no** observed-evidence authority and **no** successful-reconstruction authority;
- narrows `5211652` §8 to permit **exactly one** mechanism — a **real** `sqlite3.Row` from an in-memory `SELECT`
  (§5) — which is **NOT** a "fake `sqlite3.Row`", **NOT** a mock, **NOT** monkeypatch, **NOT** production-database
  SQL corruption, and **NOT** an adapter bypass of a real store (there is no successful store to bypass — the input
  is a standalone invalid row);
- applies **only** to the closed negative cases of §7 and the rejection tests of §9.

---

## 4. Fixture Location & Import Isolation (binding)

One future tests-only helper: **`tests/fixtures/phase6_2_negative_evidence_rows.py`**.

- It **MUST NOT** live under `phase6_2_shadow_intent/`.
- **Production / runtime modules MUST NOT import** tests, test fixtures, pytest, mocks, or this helper.
- A future **static import-direction lock** is mandated: **any production import from `tests/fixtures` is a test
  failure** (a lock test scanning `phase6_2_shadow_intent/*.py` for any `tests` / `tests.fixtures` import). This
  lock is planned here and authored within the slice that introduces the helper (§15).

---

## 5. Exact Physical Representation (binding)

The future helper may create **only a real `sqlite3.Row`** using:

- `sqlite3.connect(":memory:")`;
- `row_factory = sqlite3.Row`;
- **one parameterized `SELECT`** with **exactly these aliases**: `observation_kind`, `family_descriptor`,
  `artifact_locator`, `physical_record_position`, `provenance_timestamp`, `canonical_text_payload`.

**No table creation is required or permitted** (the `SELECT` binds literals/parameters into the six aliases). 

**Explicitly forbidden:** filesystem / temp-file / production database paths; `CREATE` / `INSERT` / `UPDATE` /
`DELETE` / `DROP`; production S1 adapter mutation or private-connection access; monkeypatch, mock row, **fake**
`sqlite3.Row`, generic dict substitution; importing private S1 SQL constants; network or persistent state. The Row
is a **genuine** `sqlite3.Row` (the real type, with the real column-name surface) carrying **intentionally invalid
values** — nothing is mocked or faked.

---

## 6. Closed Fixture API (binding)

The helper is a **closed case selector, NOT a generic arbitrary-row factory.** It may expose **only one
fixed-shape negative-row builder** over the **closed negative-case vocabulary** of §7, plus the **minimal opaque
identity/context values** the test needs (e.g. the opaque Silver pair and a context tuple).

**Forbidden:** any arbitrary payload callback, raw SQL input, arbitrary column map, extra members, or
caller-controlled **successful** payload. The caller selects a closed case + supplies minimal opaque identity; it
cannot author an arbitrary or valid row.

---

## 7. Closed Malformed Cases (binding)

Authorized — **exactly** these seven negative categories, no eighth/open-ended category without a separate charter:

1. `ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT`
2. `ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT`
3. `ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT`
4. `MALFORMED_CANONICAL_JSON`
5. `MALFORMED_SCORE_INPUTS_SUMMARY`
6. `INVALID_S1_DECIMAL_LEXIS`
7. `INVALID_PROVENANCE_TIMESTAMP`

---

## 8. Mandatory Poison Invariant (binding)

Every generated fixture is **intentionally invalid** and **MUST** satisfy **all** of:

- **expected result is `HardFailure` only**;
- **no** `INTENT_RECORDED`, `HYPOTHETICAL_CONDITION_MET`, `INTENT_EXPIRED`, or `INTENT_RETIRED` transition;
- **no** `NextShadowSnapshot`;
- **no** `NextSeenTargetPairs` commit;
- **no** partial proposal exposure;
- **no** successful reconstruction result;
- **no** S4 HALT conversion;
- **no** retry / recovery / default / repair / normalization.

**If any negative fixture yields a successful projection or any next snapshot, the test MUST fail.** The fixture is
poison: its only valid effect is to be rejected.

---

## 9. Usage Boundary (binding)

Negative fixtures may be used **only** by future rejection tests for:

- **Slice C** — `s1_evidence_projection` (whitelist/consistency/lexis rejection);
- **Slice E** — `atomic_replay_step` `HardFailure` propagation / atomicity (no snapshot, no partial commit);
- **Slice F** — `reconstruction` fold failure / no-result behavior.

They **MUST NOT** be used by Slice A/B/D happy paths, successful integration tests, determinism-success tests,
lifecycle-success tests, or runtime examples.

---

## 10. Happy-Path Authority (binding, unchanged)

All successful S1 / reconstruction tests remain **adapter-only**:

- a **temporary SQLite S1 audit fixture**;
- populated **exclusively** through `S1DurableSqliteSink.record_observation`;
- replayed through the **ratified append-order replay boundary**;
- **no** hand-rolled successful row or direct state fixture.

**The negative exception MUST NOT weaken this rule.** Successful evidence has exactly one source: the ratified
adapter.

---

## 11. Exact Malformed Construction (binding)

For each closed case, **exactly one required invariant is malformed where practical**, while all other row fields
remain **structurally valid enough to reach the intended rejection branch** (so the test proves the **specific**
rejection, not an incidental one):

- **disagreement cases** (1–3) preserve **valid JSON** but make the named row/payload values **unequal** (the column
  contradicts its embedded payload counterpart);
- **`MALFORMED_CANONICAL_JSON`** (4) is **syntactically invalid** `canonical_text_payload`;
- **`MALFORMED_SCORE_INPUTS_SUMMARY`** (5) uses a **valid JSON** payload whose `score_inputs_summary` is **missing,
  wrong-arity, or contains a non-text scalar**;
- **`INVALID_S1_DECIMAL_LEXIS`** (6) violates the **exact Phase 5 S1 lexical contract** (`^-?\d+(\.\d+)?$`);
- **`INVALID_PROVENANCE_TIMESTAMP`** (7) is **negative, non-integer, or row/payload-inconsistent** per its selected
  case.

**No fixture may be "repaired" before classification** — the invalid value reaches the production rejection path
verbatim.

---

## 12. Isolation & Lifecycle (binding)

- Each builder call creates a **fresh in-memory SQLite connection**.
- It produces **exactly one `sqlite3.Row`**, **closes the connection**, and **returns no connection/cursor**.
- **No** cross-test reuse, cache, singleton, module-level mutable store, randomness, clock, UUID, or environment
  dependency.
- **Fixture generation must be deterministic** (same case + same opaque inputs ⇒ same Row).

---

## 13. Runtime Contract (binding)

- **Runtime code must remain UNAWARE** of whether an invalid `sqlite3.Row` originated from a fixture.
- **No** test-only flag, fixture marker, bypass branch, environment variable, or alternate parser path may enter
  production code.
- **The exact same production rejection path** must process the invalid row that processes any other row. The
  fixture changes the **input**, never the **code path**.

---

## 14. Failure Taxonomy (binding)

- Each case maps to the **already-ratified expected `HardFailure` category** (`457d279` / `5211652`); the fixture
  asserts rejection, it does not define new failure semantics.
- **Fixture code must not invent lifecycle states or S4 HALTs.**
- **Unexpected fixture / programmer defects remain ordinary test failures**, never asserted as expected
  `HardFailure`.
- **Deterministic failure precedence remains governed by `457d279` / `5211652`** (order-independent, atomic, no
  partial snapshot).

---

## 15. Status & Next Gate (ratified)

- **`5211652` remains ratified as the planning charter and correctly identified the blocker.** This charter closes
  **only** the negative-fixture authorization blocker; **it implements nothing.**
- **Once this charter is ratified, the first executable gate becomes the separately-authorized Slice A — Logical
  Model TDD** (Slice A has no S1 dependency and needs no fixture).
- **Fixture implementation itself remains DEFERRED** until the first slice that requires it — **Slice C RED tests**
  (`tests/fixtures/phase6_2_negative_evidence_rows.py` + its import-direction lock are authored there, not before).
- **No direct Slice C / E / F or runtime jump is authorized.** Slices proceed in DAG order (A → B → C → …), each its
  own human-authorized "Begin…" task.
- **Phase 6.2 remains UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0
  emit sites); production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** the `5211652` §8 fixture blocker is closed by authorizing **exactly one** quarantined, tests-only
negative-evidence mechanism — a future `tests/fixtures/phase6_2_negative_evidence_rows.py` helper that builds a
**real `sqlite3.Row`** via `sqlite3.connect(":memory:")` + `row_factory = sqlite3.Row` + one parameterized `SELECT`
aliasing exactly the six replay columns (no table, no temp file, no production DB, no `CREATE/INSERT/UPDATE/DELETE/
DROP`, no adapter mutation/private-connection access, no monkeypatch/mock/**fake**-Row/dict substitution, no private
SQL-constant import, no network/persistent state), exposed as a **closed case selector** (not a generic factory)
over the **seven** closed categories (`ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT`,
`ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT`, `ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT`, `MALFORMED_CANONICAL_JSON`,
`MALFORMED_SCORE_INPUTS_SUMMARY`, `INVALID_S1_DECIMAL_LEXIS`, `INVALID_PROVENANCE_TIMESTAMP`) plus minimal opaque
identity/context. Every fixture is **poison**: its only valid outcome is `HardFailure` — **no** lifecycle
transition, **no** `NextShadowSnapshot`, **no** `NextSeenTargetPairs` commit, **no** partial proposal, **no**
successful result, **no** S4-HALT conversion, **no** retry/repair/normalization — and any successful projection or
next snapshot **fails the test**. Each case malforms **exactly one** invariant while keeping the rest valid enough to
hit the intended branch, is **never repaired** before classification, is processed by the **same production
rejection path** with the runtime **unaware** of fixture origin (no test-only flag/branch/env/alternate parser), is
**deterministic** (fresh `:memory:` connection, one Row, connection closed, no cache/clock/UUID/env), and is usable
**only** by Slice C/E/F rejection tests — **never** by happy/determinism/lifecycle-success paths. **All successful
S1/reconstruction evidence remains adapter-only** (temp SQLite populated **exclusively** via
`record_observation`, replayed through the ratified boundary; the negative exception does **not** weaken this), the
**absolute ban on synthetic successful evidence / successful transitions / fabricated intent state / alternate
observed-event sources stands**, and failure taxonomy stays governed by `457d279`/`5211652`. **Blocker: CLOSED.**
The **first executable gate is the separately-authorized Slice A — Logical Model TDD**; fixture implementation is
**deferred to Slice C RED**; no Slice C/E/F or runtime jump is authorized. **Phase 6.2 remains UNBUILT and NOT
runtime-ready. No executable work is authorized.**
