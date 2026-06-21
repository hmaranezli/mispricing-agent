# Phase 6.1 — S5 Runner In-Memory Orchestration Runtime Closeout & Ratification Charter

> **This is a docs-only closeout/ratification charter.** It formally seals the **already-built, already-pushed**
> S5 in-memory orchestration runtime (commit `d1fede8`) as a **test-only passive runner**. It **builds nothing**:
> no runtime code, no tests, no schema, no adapter. It authorizes NO new runtime, NO tests, NO lock-test edits, NO
> frozen-component edits, NO S1 durable storage, NO live/paper/canary, NO production durability, NO
> execution/actionability, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_cell3_passive_cost_context_source_runtime_closeout_ratification.md`,
> `docs/handoff/phase6_1_b2_pass_path_ingestion_runtime_closeout_ratification.md`, the Reader / S2 / B2 / B3 /
> Producer / B4 / S4 / S1 charters, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `d1fede835000fbe9e9a36433c42f4b4f6f095883`

**Sealed artifact:** commit `d1fede8` — `feat(phase6_1): add S5 in-memory runner orchestration` (parent `bcaa8f0`).

---

## 1. Base / Purpose

**Base commit:** `d1fede835000fbe9e9a36433c42f4b4f6f095883`.

With the S5 in-memory runner now **BUILT** (`d1fede8`) via a clean RED→GREEN TDD cycle, this charter **ratifies**
it as a **dumb, strictly-synchronous, test-only passive coordinator** of the frozen
Reader → S2 → {pass path | halt path} → S1 reference-sink pipeline. It records the verification facts and the
equal-peer / fail-fast / dumb-wire-harness seals, and restates the precise state and remaining gates. It claims
**no** new capability, **no** durable storage, and **no** pass-path-to-production readiness.

**No capacity validation and no capacity pass is claimed by this charter** (see §14).

---

## 2. Strict 2-File Runtime Seal (ratified)

The runtime slice touched **exactly two files** and nothing else:

- `phase6_1/s5_runner.py` — the dumb in-memory coordinator;
- `tests/test_phase6_1_s5_runner.py` — its 16-test pin.

**No** edit was made to any frozen component: **no** change to the Option-B reader, S2 identity wiring, B2 ingestion
/ normalizer / `PublicRawSnapshotRecord`, Cell-3 cost-context source, B3, Producer, Phase 5, B4, S4, S1, or **any**
lock test. The five pre-existing untracked files were left untouched.

---

## 3. Evidence-First API Seal (ratified)

S5 was authored **only after** inspecting the frozen public API chain from source, and it uses each component's
existing public entrypoint **without inventing any adapter, shim, or reshape**:

- `read_option_b_event_stream(*, text_stream, artifact_locator)` (generator of `OptionBEventEnvelope`);
- `route_option_b_envelope_to_s2_identity_candidate(*, envelope)` → `S2IdentityWiringCandidate`;
- `ingest_pass_path_snapshot_record(*, parsed_payload, market_provenance_context,
  gross_edge_binding_label_context)` → `PublicRawSnapshotRecord`;
- `normalize_replay_snapshot_to_evidence_material(*, raw_snapshot, evidence_epoch_tolerance_ms)` →
  `NormalizedEvidenceMaterial`;
- `build_passive_zero_cost_validity_contexts()` → the length-1 cost-context tuple;
- `wire_passive_shadow_input(*, normalized_evidence_material, cost_validity_contexts)` → `PassiveShadowInput`
  (pass) or a returned carrier;
- `build_passive_observation_record(*, pass_handoff, identity_evidence, opaque_cost_context)` →
  `ObservationScoreRecord` / `materialize_passive_halt_record(*, halt_source, identity_evidence,
  opaque_cost_context)` → `ObservationHaltRecord`;
- `S1InMemoryObservationSink.record_observation(record)`.

The contract chain was **complete** (no API gap), so no blocker was raised and no adapter was invented.

---

## 4. Pass-Path Seal (ratified)

A valid pass line flows, in order: **B2 ingestion → B2 normalizer → Cell-3 zero-cost source → B3 →
`PassiveShadowInput` → B4 → `ObservationScoreRecord`** recorded in S1. The cost unit `"proportion"` and the gross
unit `"proportion"` cohere as the identical token in `calculate_net_edge`, so the record's
`family_payload["passive_score_magnitude"] == "7"` (**net == gross**, zero carried cost). S5 reads no payload
field; it only hands objects to the frozen components.

---

## 5. Halt-Path Seal (ratified)

A malformed line becomes an `OptionBLocalParseHalt` in the reader's payload slot, is carried unchanged by S2, and
is materialized by **S4 → `ObservationHaltRecord`** recorded in S1, with
`family_payload["halt_family_descriptor"] == "passive_local_parse_halt"`. The **same** `OptionBLocalParseHalt`
object is preserved both as `family_payload["halt_origin_reference"]` and as the S2 candidate's
`forwarded_payload_or_local_halt` (proven by `is` identity) — never dropped, copied, or reclassified.

---

## 6. Equal-Peer Chronology Seal (ratified)

For a stream of one pass line then one malformed line, S1's `snapshot()` holds **exactly two records in
chronological order**: `ObservationScoreRecord` (SCORE) then `ObservationHaltRecord` (HALT). S5 records both
families as **equal peers** — no prioritization, ranking, filtering, reordering, business evaluation, threshold,
or actionability. SCORE and HALT are neutral peer outcomes of the same coordinator.

---

## 7. Fail-Fast Crash Boundary (ratified)

Raw component/structural crashes propagate as **hard exceptions that bypass S4 entirely** — they are **never**
wrapped into an `ObservationHaltRecord` and **never** swallowed:

- a parsed dict missing a required key → `B2PassPathIngestionValueError` propagates (sink stays empty — no halt
  manufactured);
- a parsed non-dict payload (e.g. a JSON array) → `B2PassPathIngestionTypeError` propagates (sink empty);
- an unexpected client-wiring output (neither `PassiveShadowInput` nor a ratified `BlockedPacket`) →
  `S5RunnerUnexpectedOutputError` hard-fails (sink empty).

S5 contains **no** `try`/`except` (AST-proven): only the reader's ratified structural halt carrier
(`OptionBLocalParseHalt`) and a returned ratified `BlockedPacket` reach S4; everything else fails fast.

---

## 8. Dumb Wire-Harness Affirmation (ratified)

S5 is a **dumb wire-harness**: it **generates no** provenance, binding labels, identity, payload fields, cost-context
constants, timestamps, cursors, offsets, or storage state. It builds **no** dict/object of its own (AST-proven: no
`ast.Dict`). It **consumes caller-injected** passive contexts — the single `MarketProvenanceContext` and
`GrossEdgeBindingLabelContext` supplied as explicit inputs — and applies them to the single pass event of the
fixture. The cost-context tuple is obtained from the frozen Cell-3 source (not manufactured by S5) and carried
opaquely; identity is the S2 candidate, carried unchanged.

---

## 9. No Multi-Event Provenance Claim (ratified)

`d1fede8` is **NOT** a general multi-event / multi-stream provenance solution. The single caller-supplied
`MarketProvenanceContext` / `GrossEdgeBindingLabelContext` are sufficient **only** for the single-pass-event
fixture. Any future per-event context **registry / resolver / lookup / cache / matching / provider** is a
**separate architectural boundary outside S5** and must be separately chartered; S5 itself must remain free of such
logic (AST/text-locked: no dict, no registry/resolver/lookup/cache/matching tokens).

---

## 10. Clean EOF Seal (ratified)

Natural reader exhaustion is a **passive clean stop**: an empty stream yields an **empty sink** and a clean return;
a single pass line yields **exactly one record** with **no synthetic trailing record**. There is **no** synthetic
EOF record, **no** halt on exhaustion, **no** readiness token, **no** reconnect, and **no** polling loop.

---

## 11. AST / Text Lock Ratification (ratified)

The 16-test suite AST/text-locks the module:

- **strictly synchronous** — no `async def` / `await` / `yield` / `yield from` / `async for` / `async with` /
  `while`; S5 is not a generator and runs no event/polling loop (it drives one synchronous `for` over the reader);
- **no `try`/`except`** (no exception swallowing); **no `isinstance`** (exact-type discipline);
- **imports only** `phase6_1` / `phase5` roots; **no** concurrency or IO imports (asyncio/threading/
  multiprocessing/queue/concurrent/socket/sqlite3/pickle/json/os/sys/pathlib/io/time);
- **no per-event context dict/registry** (no `ast.Dict`; no registry/resolver/lookup/cache/matching tokens);
- **no durable-storage / serialization surface** (no sqlite/parquet/pickle/`open(`/serialize/checkpoint/durable/
  persist);
- the **package-wide** forbidden-token / forbidden-import / no-`isinstance` / name-surface locks remain green for
  the new module (incl. the `candidate`-token fix in §12).

S5 defines exactly one function (`run_in_memory_shadow_pipeline`) and one error type
(`S5RunnerUnexpectedOutputError`).

---

## 12. Testing Discipline Seal (ratified)

- A **real RED→GREEN** cycle: RED was `ModuleNotFoundError` (module genuinely absent), then a minimal GREEN.
- New suite: **16 passed / 16** (pass-path, halt-path, equal-peer order, identity carriage, EOF ×2, crash boundary
  ×3, signature, context discipline, AST/sync/import/storage locks).
- Locks + Reader/S2/B2/Cell-3/B3/B4/S4/S1/Producer peers: **226 passed / 0 failed**.
- The first-GREEN failures were **self-inflicted** — docstring prose collisions (`durable`/`serialization`/
  `registry`/`lookup`/`cache`/`matching`, the forbidden token `Routing`) and a bare `candidate` **variable name**
  (a forbidden token; the S2 module avoids it by underscore-gluing). All were fixed by **scrubbing/renaming the
  code to conform to the locks** (variable → `identity_candidate`), **not** by weakening any test — per the standing
  "conform the code, never weaken the test" precedent. **Zero regressions. No** broad `pytest` (scope was the new
  suite + locks + the directly orchestrated peers).

---

## 13. Precise State (ratified)

- **S5 in-memory orchestration: BUILT + RATIFIED for TEST-ONLY purposes** (`d1fede8`).
- This **does NOT** authorize S1 durable storage, live / paper / canary, production durability, execution,
  routing, actionability, or Phase 6.2 readiness.
- The full passive in-memory pass+halt run is now demonstrable end-to-end against the **in-memory S1 reference
  sink** only.

---

## 14. Remaining Gates

- **Phase 6.1: INCOMPLETE** until separately closed out (a Phase 6.1 in-memory pipeline closeout/ratification
  charter is the natural seal). **Phase 6.2: NOT ready.**
- **S1 durable storage: a SEPARATE downstream gate** (persistence / retention / production durability), **UNBUILT**;
  the S1 sink remains a **test-only reference sink**.
- **Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit sites**;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."
- **live / paper / canary / execution / actionability: FORBIDDEN.**

---

## 15. Next Safe Step

Exactly one of the following, and **only** if separately commanded — neither is opened by this charter:

- a **separately-authorized Phase 6.1 in-memory pipeline closeout / ratification charter** (sealing the full
  passive in-memory pass+halt run as Phase 6.1's in-memory milestone); **or**
- a **separately-authorized S1 storage-medium charter** (durable persistence / retention, the separate downstream
  gate).

A general multi-event context-supply boundary (§9) is likewise separately gated. **No implementation is authorized
by this charter.**

**Conclusion:** the S5 in-memory runner (`d1fede8`) is **ratified and sealed as a test-only passive coordinator** —
a strict-2-file, evidence-first, dumb, strictly-synchronous wire-harness that drives the frozen
Reader → S2 → {pass path | halt path} → S1 reference sink one record at a time to natural EOF. **Pass-path** (B2
ingestion → normalizer → Cell-3 → B3 → `PassiveShadowInput` → B4 → `ObservationScoreRecord`, `passive_score_magnitude
== "7"`) and **halt-path** (`OptionBLocalParseHalt` → S4 → `ObservationHaltRecord`, same object preserved) are
recorded as **chronological equal peers**; raw crashes (`B2PassPathIngestionValueError` /
`B2PassPathIngestionTypeError` / unexpected wiring output) **fail fast, bypassing S4**, with no swallowing and no
manufactured halt; EOF is a **passive clean stop**; S5 **generates no** provenance/identity/labels/payload/cursors/
storage and consumes caller-injected contexts for the **single-pass-event fixture only** (explicitly **not** a
multi-event provenance solution). Verification: **16/16** new, **226 passed / 0 failed** across locks + peers, zero
regressions, no broad pytest, scrub/rename-as-conform. **S5 in-memory orchestration is BUILT + RATIFIED for
test-only purposes**; it **does not** authorize S1 durable storage, live/paper/canary, production durability,
execution, routing, actionability, or Phase 6.2 readiness. **Phase 6.1 remains incomplete; S1 durable storage and
the capacity gate remain separate; live/paper/canary/execution/actionability remain forbidden.** **No executable
work is authorized.**
