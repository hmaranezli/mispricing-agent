# Phase 6.1 Option-B Reader Implementation TDD — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It permanently seals the **completed** Option-B
> event-stream reader IO boundary, its output contract, and its authorized narrow `json` lock exception (commit
> `5fece9f`). It **builds and designs nothing**. It authorizes NO runtime code, NO tests, NO lock-test edits, NO
> Python/schema/runtime/interface edits, NO B1/B2/B3/Phase 5/producer changes, NO S2 wiring, NO Slice-0B schema,
> NO B4 scoring, NO S4 materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify.
> It is subordinate to
> `docs/handoff/phase6_1_option_b_reader_io_design_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_option_b_event_level_replay_artifact_contract_amendment_charter.md`,
> `docs/handoff/phase6_1_option_b_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `5fece9fd479a07204bf6aaebfcb14f2a12fce8e1`

---

## 1. Base / Dependency Chain

**Base commit:** `5fece9fd479a07204bf6aaebfcb14f2a12fce8e1`.

References:

- `…_option_b_reader_io_design_charter.md` — defined the reader as a dumb, blind, deterministic physical parser
  emitting the tripartite envelope `(parsed_payload_or_local_halt, artifact_locator, physical_record_position)`.
- `…_option_b_serialization_field_shape_charter.md` — pinned the JSONL-style line-oriented at-rest shape; medium
  identity is IO-layer metadata, never in payload.
- `…_option_b_event_level_replay_artifact_contract_amendment_charter.md` — 1:1 physical-record-to-event invariant;
  INVALID batched/nested/multi-event/snapshot-container shapes.
- `…_option_b_reader_io_lock_exception_amendment_charter.md` — authorized, at docs level, a TOKEN-ONLY `json`
  exception for exactly one basename (`option_b_event_stream_reader.py`), with no `open`/IO/path capability.

**Implemented commit under closeout:** `5fece9f` (parent `1f97a68`).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Closeout Exists

The Option-B reader is implemented and green; it is the first executable code in the Option-B chain. Before any
further track (S2 identity wiring, real-cost Cell-3, B4 scoring, durable logs), the reader's guarantees must be
**frozen as ratified invariants** so no later step can mutate the IO boundary, smuggle filesystem/`open`/path
capability, widen the `json` exception, read a clock, mint identity, weaken a package-wide lock, or break the
tripartite output contract or medium/payload separation. This charter records the proof and seals those
invariants; it advances nothing executable.

---

## 3. Evidence Inventory (recorded)

- **Commit:** `5fece9f` — `feat(phase6_1): add option b event stream reader`.
- **Strict 4-file boundary** (exactly these, nothing else):
  - `phase6_1/option_b_event_stream_reader.py` (new, +92)
  - `tests/test_phase6_1_option_b_event_stream_reader.py` (new, +296)
  - `tests/test_phase6_1_forbidden_token_locks.py` (+15/−1)
  - `tests/test_phase6_1_diagnostic_ev_non_actionability.py` (+15/−1)
  - Totals: **4 files changed, +416 / −2**. No B1/B2/B3/Phase 5/producer/`PassiveShadowInput`/docs/config/data
    file touched.
- **Reader suite:** **23/23 passed** (`tests/test_phase6_1_option_b_event_stream_reader.py`).
- **Combined lock verification:** **46 passed** (reader suite + both full lock-test files), proving the `json`
  exception is narrow — the package-wide **import** and **IO/dynamic-exec** scans passed for the Option-B reader
  **without** any import/`open` exception.
- **No broad pytest.** Only the targeted reader suite and the two package-wide lock-test files were run (the latter
  *are* the package-wide locks).

---

## 4. Island Seal (RATIFIED)

The Option-B reader is **BUILT and frozen as an isolated stream generator**:

- It yields `OptionBEventEnvelope` from **caller-injected text streams** only (e.g. `io.StringIO`).
- It is **NOT wired** to B1, B2, B3, the passive producer, Phase 5, S1, S2, B4, S4, or S5. It imports none of them
  and is called by none of them. It is a standalone island.
- Freezing: any change to its signature, behavior, or boundary requires **separate authorization**.

---

## 5. Tripartite Envelope Seal (RATIFIED)

- `OptionBEventEnvelope` is the **permanent output contract** for this reader: one immutable envelope per physical
  line, carrying `parsed_payload_or_local_halt`, `artifact_locator`, `physical_record_position`.
- **Immutable and non-dict.** The envelope is a frozen, slotted carrier (proven by tests: `type(env) is not dict`,
  `not isinstance(env, dict)`, and attribute reassignment raises).
- **Medium identity rides alongside, not inside.** `artifact_locator` and `physical_record_position` are the 2nd/
  3rd envelope parts — never serialized into, nor read from, the payload. Payload-authored identity fields
  (`event_id`/`row_offset`/`uuid`/…) are left inside the payload and never promoted to envelope identity (proven
  by test).
- **No bare-payload emission.** The reader never yields a plain payload object alone.

---

## 6. Guardrail Containment (RATIFIED)

- The `json`-token exception is **permanently capped to exactly one basename**:
  `option_b_event_stream_reader.py`.
- It is **token-only**: no `open()`, `os`, `pathlib`, `sys`, `io` import or path capability is authorized for that
  basename. The reader is **stream-only** and opens nothing.
- **No package-wide Phase 6.1 JSON authorization** is implied. Every other `phase6_1/*.py` module remains fully
  under the `json`-token ban.
- If the reader module is renamed or removed, the exception lapses; no other module inherits it.

---

## 7. Lock-Test Ratification (RATIFIED)

The two package-wide lock-test files were amended **only** with basename-specific `json` allowlist logic:

- `tests/test_phase6_1_forbidden_token_locks.py`
- `tests/test_phase6_1_diagnostic_ev_non_actionability.py`

Specifically, each gained a TOKEN-ONLY constant block (`_OPTION_B_READER_BASENAME` +
`_OPTION_B_READER_TOKEN_ALLOWLIST = {"json"}`) and routed its **forbidden-token scan** through a per-basename
allowlist lookup. **Unchanged and intact:** the import scans, the IO/`open` scans, `_open_is_read_only`, the
`_FORBIDDEN_TOKENS` set, the assertion semantics, and every package-wide guardrail. The amendment is
behavior-preserving for the existing single-artifact reader (`b1_replay_depth_artifact_reader.py` → `{"json"}`),
adds `option_b_event_stream_reader.py` → `{"json"}`, and maps every other basename → `frozenset()`. No guardrail
was weakened or broadened.

---

## 8. S2 Block Affirmation (RATIFIED)

- Although the reader **emits the Silver tuple components** (`artifact_locator`, `physical_record_position`), **S2
  Identity remains BLOCKED.**
- The tuple is **not yet wired or carried as ratified pipeline evidence**: the reader is an island (§4); nothing
  consumes its envelope as a durable identity source. The opaque S2-owned identity slot stays **unfilled**.
- **Future S2 work must consume the reader as a client** — it must **not** mutate, widen, subclass, wrap,
  monkeypatch, or refactor the reader or its envelope. The reader is a frozen boundary; S2 borrows from it, it
  does not reshape it.
- **Slice-0B field-level schema remains BLOCKED** until S2 holds an authoritative carried borrowed identity
  source.

---

## 9. Halt Schema Isolation (RATIFIED)

- `OptionBLocalParseHalt` is a **local IO-layer parse-halt payload only** — an immutable marker carrying the
  malformed physical line verbatim, surfaced (never raised, never dropped) for a line that is not valid JSON.
- It **does NOT** define, authorize, inherit from, or replace the **future S4 global halt materialization
  schema**. It is not an S4 record, not a shadow-log entry, and implies no S4 design. How (or whether) a local
  parse-halt is ever materialized into a durable log is **S4's**, separately gated.

---

## 10. Runtime Invariants Frozen (RATIFIED — AST-proven)

Frozen for `phase6_1/option_b_event_stream_reader.py` and proven by the reader suite's AST locks:

- **Stream-only** — operates on a caller-supplied text stream; **no filesystem crawling, no `open()`, no path
  derivation**; no `os`/`pathlib`/`sys`/`io`/`shutil`/`tempfile`/`glob` imports.
- **Intrinsic IO position** — `physical_record_position` comes only from the active stream's own position
  mechanics (`tell()` before `readline()`); **no `enumerate`, no global/application/persisted/cross-file
  counters**, and **no `global` statement**.
- **No identity minting / no clock** — no `uuid`/`hashlib`/`random`/`secrets`/`time`/`datetime`/`calendar`.
- **No upstream coupling** — no `phase5` / `phase6_1.b1` / `phase6_1.b2` / `phase6_1.b3` /
  `phase6_1.passive_producer` imports.
- **No semantic validation** — structural `json.loads` parse only; no price/sign/unit/venue/cost/freshness/
  scoring/mapping/coercion/calibration. Proven by the "semantically absurd but syntactically valid JSON is emitted
  successfully" test.
- **Non-swallowing defensive parse** — a malformed line yields an `OptionBLocalParseHalt` envelope; the except
  handler does not `pass`/`continue`/`break`/re-raise.
- **No actionability surface** — no `edge_direction`/staleness/capacity/Shadow Intent/sizing/routing tokens; **no**
  S4/B4/S5/Cell-3/Phase 6.2 behavior.

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Still-Forbidden Work

- **No** change to the ratified reader surface (§4) or its envelope contract (§5); **no** mutation/widening/
  subclass/wrap/monkeypatch of the reader.
- **No** widening of the `json` exception; **no** `open`/`os`/`pathlib`/`sys`/`io`/path capability for the reader;
  **no** package-wide JSON authorization.
- **No** further lock-test edit; **no** weakening of any package-wide import/IO/token guardrail.
- **No** S2 identity wiring/fill; **no** Slice-0B field-level schema; **no** promotion of the Silver tuple to
  carried evidence here.
- **No** promotion of `OptionBLocalParseHalt` into an S4 materialization schema or shadow-log record.
- **No** `enumerate`/counter/clock/identity-minting in the reader; **no** semantic validation.
- **No** B1/B2/B3/Phase 5/producer change; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized track** — choose one: (a) an **Option-B reader → S2 identity wiring** planning charter
  (S2 consumes the reader **as a client**, borrowing the `(artifact_locator, physical_record_position)` tuple as
  carried evidence, without reshaping the reader); (b) the **real-cost Cell-3 cost-context assembly** charter
  (parallel; Phase-6.2 fidelity dependency); or (c) a **B4 passive shadow scoring** planning charter. Each is
  docs-first and separately gated.
- **No implementation is authorized by this charter.** S2 identity wiring/fill, the Slice-0B schema, S4
  materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the Option-B event-stream reader is **BUILT + RATIFIED** at `5fece9f` — a frozen, isolated,
stream-only physical parser whose permanent output contract is the immutable non-dict tripartite envelope
`OptionBEventEnvelope(parsed_payload_or_local_halt, artifact_locator, physical_record_position)` (medium identity
alongside, never inside, the payload); its `json` exception is **permanently capped, token-only, single-basename**
with no `open`/IO/path capability and no package-wide JSON authorization; the two lock files were amended **only**
with basename-specific `json` allowlist logic, leaving all import/IO scans and package-wide guardrails intact;
`OptionBLocalParseHalt` is a **local IO-layer parse-halt only**, isolated from the future S4 schema; and **S2
identity remains BLOCKED** and **Slice-0B schema remains BLOCKED** because the Silver tuple is not yet wired as
ratified pipeline evidence. Evidence: **23/23** reader suite, **46 passed** combined lock verification, **strict
4-file** boundary, **no broad pytest**. Phase 6.1 remains **incomplete**; Phase 6.2 remains **not ready**. **No
executable work is authorized.**
