# Phase 6.1 — S4 Halt-Materialization Runtime TDD Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It permanently seals the **completed** S4 halt-
> materialization runtime slice (commit `3851803`). It **builds and designs nothing**. It authorizes NO runtime
> code, NO tests, NO lock-test edits, NO schema/runtime/interface edits, NO edits to the Option-B reader /
> `S2IdentityWiringCandidate` / B3 / B4 / the S1 reference sink, NO S5 runner, NO storage-medium/persistence design,
> NO Cell-3 assembly, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s4_exception_routing_halt_materialization_decision_charter.md`,
> `docs/handoff/phase6_1_s4_halt_payload_field_shape_charter.md`,
> `docs/handoff/phase6_1_s4_halt_payload_field_shape_narrowing_amendment.md`,
> `docs/handoff/phase6_1_b4_passive_scoring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `3851803be1e7d4da1b6807532e3209d63a82a53d`

---

## 1. Base / Dependency Chain

**Base commit:** `3851803be1e7d4da1b6807532e3209d63a82a53d`.

References:

- `…_s4_exception_routing_halt_materialization_decision_charter.md` — decided S4 as a passive, recorder-oriented
  halt-materialization boundary under the **Mortician Rule**; **S4 ≠ S1 sink**.
- `…_s4_halt_payload_field_shape_charter.md` — defined the narrow, closed halt payload obligations.
- `…_s4_halt_payload_field_shape_narrowing_amendment.md` — renamed/narrowed `halt_inputs_summary` to
  `opaque_upstream_context` (pre-existing passive context by reference **or `None`**; never manufactured).
- `…_b4_passive_scoring_runtime_tdd_closeout_ratification.md` — the green **score** path peer; the halt path is its
  equal-peer counterpart.
- `…_s1_in_memory_reference_sink_tdd_closeout_ratification.md` — the S1 sink admits an exact `ObservationHaltRecord`
  by exact type and records it.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — the opaque Silver pair carried by
  `S2IdentityWiringCandidate`.

**Implemented commit under closeout:** `3851803` (parent `c1047cd`).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- The S4 halt-materialization runtime is **implemented and green** (`3851803`): a pure, deterministic function that
  packages one already-observed structural halt carrier into one `ObservationHaltRecord` for the S1 reference sink.
- The passive evaluation spine (Phase 5 socket, passive producer, Master B3), the Option-B reader,
  `S2IdentityWiringCandidate`, the S1 in-memory reference sink, and the B4 passive scorer remain **BUILT + RATIFIED
  and frozen**.
- **Both observation paths are now green and equal-peer:** the **score** path (B4 → `ObservationScoreRecord` → S1)
  and the **halt** path (S4 → `ObservationHaltRecord` → S1). S5, durable storage, and Cell-3 remain unbuilt/unbound
  (§10). Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. Ratified Implementation Facts (from `3851803`)

- **Commit:** `3851803` — `feat(phase6_1): add s4 halt materialization runtime` — a **strict 2-file runtime + test
  slice**:
  - `phase6_1/s4_halt_materialization.py` (new, +69)
  - `tests/test_phase6_1_s4_halt_materialization.py` (new, +372)
  - Totals: **2 files changed, +441**. No lock-test, docs, reader, S2 candidate, B3, B4, S1 sink, producer, Phase 5,
    config, data, or storage file touched.
- **Public function (RATIFIED):** `materialize_passive_halt_record(*, halt_source, identity_evidence,
  opaque_cost_context)` — keyword-only, pure, stateless, deterministic. Frozen; any signature/behavior change
  requires **separate authorization**.
- **Verification (RATIFIED):** S4 suite **22/22**; **both full package-wide lock files passing** (no lock edit, no
  allowlist); upstream **S1 sink 25/25, B4 21/21, S2 wiring 20/20, Option-B reader 23/23 → 89 passed**; **zero
  regressions**; **no broad pytest**.
- **TDD discipline (RATIFIED):** real RED first (`ModuleNotFoundError` for the missing module — feature absent), then
  minimal GREEN.

---

## 4. Authorized Halt Carriers (RATIFIED)

- S4 admits **exactly three** already-observed structural halt carrier types, all **located in existing code without
  editing any upstream module**:
  - `OptionBLocalParseHalt` — `phase6_1/option_b_event_stream_reader.py`;
  - `B3PassiveClientWiringError` — `phase6_1/b3_passive_client_wiring.py`;
  - `BlockedPacket` — `phase5/blocked_result_boundary.py`.
- **No invented, stubbed, faked, or placeholder halt carrier type** was created. The pre-flight blocker check passed:
  every dependency type was importable as-is.

---

## 5. Exact-Type Gate (RATIFIED)

- `halt_source` is admitted **only** by **exact type identity** via a static type-keyed lookup
  (`type(halt_source)`), with **no `isinstance`** anywhere (AST-proven by the slice and by the package-wide
  no-`isinstance` lock).
- **Unknown types and subclasses are rejected** (`TypeError`): a subclass of any authorized carrier has a distinct
  exact type that is not a mapping key, so it never matches (proven for an `OptionBLocalParseHalt` subclass and a
  `BlockedPacket` subclass). A plain `TypeError` instance, dict, list, str, int, and bare object are all rejected.

---

## 6. Zero-Object-Inspection Seal (RATIFIED)

- `halt_source` is carried **opaquely, by reference**, into `family_payload["halt_origin_reference"]` — never copied,
  parsed, normalized, or rendered.
- **No `halt_source` attribute access exists anywhere** in the module (AST-proven: no `halt_source.<attr>` node), and
  the module performs **no `str` / `repr` / traceback / error-message / args / field parsing** of the carrier
  (AST-proven: no `str`/`repr`/`getattr`/`vars`/`dir` calls, no `args`/`__dict__`/`format_exc`/`print_exc` attribute
  surface). S4 does not read what the halt *says*; it records *that* the halt occurred.

---

## 7. Static Descriptor Mapping (RATIFIED)

- `halt_family_descriptor` is selected **only** from the **exact carrier type** via the static, non-versioned mapping
  `_HALT_FAMILY_DESCRIPTOR_BY_TYPE` (`passive_local_parse_halt` / `passive_client_wiring_halt` /
  `passive_blocked_packet_halt`). It is **type provenance, not severity, not taxonomy, not a ranking, not a versioned
  ID, and not identity** (proven: distinct per type, contains no `v0`/`version`/`uuid`/`id=`/`hash`).
- **The descriptor is independent of the object's contents** — two `OptionBLocalParseHalt` carriers with different
  `raw_line` content yield the **same** descriptor (proven), confirming contents are never inspected to choose it.

---

## 8. Absolute None Mandate (RATIFIED)

- **`opaque_upstream_context = None` and `provenance_timestamp = None` are intentional, ratified safety choices —
  NOT TODO placeholders, NOT stubs, and NOT pending work.**
- `opaque_upstream_context` is `None` because there is **no** pre-existing passive upstream context that can be
  borrowed by reference without inspecting the opaque cost context; per the narrowing amendment's safe-fallback rule,
  S4 **manufactures no context** (proven `None` across varied `opaque_cost_context` inputs, while the cost context
  itself is still carried opaquely at the envelope by identity).
- `provenance_timestamp` is `None` because **none was supplied and S4 reads no clock**; S4 **manufactures no time**.
- These `None`s are the **faithful representation of absence**, consistent with the Mortician Rule: S4 never
  back-fills, defaults, or synthesizes the very data whose absence the halt records.

---

## 9. Identity, Closed-Payload & Zero-Knowledge-Transport Seals (RATIFIED)

- **Identity discipline.** `identity_evidence` is admitted **only** as an exact `S2IdentityWiringCandidate` and placed
  **only** in the top-level envelope slot, by reference. **No fallback identity, no minting, no hashing, no
  collapse/derivation** (AST-proven: no `uuid*`/`sha*`/`md5`/`hexdigest`/`token_*`/`getrandbits` surface, no
  `hash()`/`id()` calls). A non-candidate and a candidate subclass are both rejected.
- **Closed payload.** `family_payload` carries **exactly** the closed three attributes — `halt_origin_reference`,
  `opaque_upstream_context`, `halt_family_descriptor` — and nothing else (proven: key set equality). It carries **no
  identity alias** and **does not leak** the candidate or its Silver pair (locator/position) in values or `repr`
  (proven).
- **Zero-Knowledge Transport.** `halt_origin_reference` is a **pure opaque carry-by-reference**. The S4 boundary
  neither stringifies, reprs, logs, nor inspects it, and this seal **binds future consumers**: anything downstream of
  S4 must treat `halt_origin_reference` as opaque and must **not** stringify/`repr`/log/parse/inspect it through the
  S4 boundary. S4 transports the halt without knowing its contents.

---

## 10. Mortician Rule & Side-Channel Seal (RATIFIED)

- **Mortician Rule (sealed).** S4 **records** an already-observed halt and **nothing more**: **no** retry, repair,
  recovery, self-heal, re-attempt, remediation, normalization, enrichment, back-fill, reconstruction, substitution,
  or synthesis of missing data.
- **No taxonomy / actionability / orchestration.** **No** severity, priority, criticality, ranking, taxonomy,
  readiness, verdict, decision, route, execution, sizing, allocation, actionability, or "should continue / should
  stop / should retry" semantics anywhere (AST + text proven; the `HALT` marker is a neutral equal-peer tag, not a
  ranking).
- **No side channel.** **No** logging import, `print`, or stdout/stderr write; **no** clock, randomness, network,
  filesystem, DB, serialization, or dynamic exec (AST-proven: none of `traceback`/`logging`/`sys`/`io`/`os`/
  `pathlib`/`json`/`hashlib`/`uuid`/`random`/`time`/`datetime` imported; no `open`/`eval`/`exec`/`print` calls).
- **S4 ≠ S1 sink.** S4 **produces** one record and returns it; **S1 records**. S4 stores, retains, and owns no log.
- **No S5 runner logic.** S4 contains **no** orchestration, selection, dispatch, looping, batching, or pass/halt
  branching; it materializes **one** observed halt into **one** record.

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." A halt is **not** a capacity decision and confers no capacity meaning.

---

## 12. Precise Status

- **The halt path is GREEN** (S4 → `ObservationHaltRecord` → real S1 reference sink) and is an **equal peer** of the
  GREEN **score** path (B4 → `ObservationScoreRecord` → real S1 reference sink). Neither family is privileged.
- **Phase 6.1 is still INCOMPLETE.** The S5 runner, the S1 durable storage medium, and the real-cost Cell-3 assembly
  remain **separately gated** and **unbuilt/unbound**. The S1 sink remains a **test-only reference sink** (no
  physical persistence). **Phase 6.2 is not ready.**

---

## 13. Still-Forbidden Work

- **No** change to the ratified S4 surface (§3) or its behavior; **no** mutation/widening/wrap of S4.
- **No** retry/repair/recovery/normalize/enrich/back-fill/synthesis; **no** taxonomy/severity/ranking; **no**
  actionability or "should continue / should stop / should retry."
- **No** `halt_source` inspection/stringify/repr/parse; **no** breach of Zero-Knowledge Transport (§9) by S4 or its
  future consumers through the S4 boundary.
- **No** identity in/from the payload; **no** fallback/minted identity; **no** `provenance_timestamp` or
  `opaque_upstream_context` manufactured (the Absolute None Mandate, §8, stands).
- **No** sink reference, storage, persistence, serialization, or DB path in S4; **no** S4-as-sink.
- **No** lock-test edit; **no** new allowlist; **no** weakening of any guardrail.
- **No** S5 runner / orchestration; **no** storage medium / durable persistence; **no** Cell-3 assembly.
- **No** edit to / reach-back into the reader, S2, B3, B4, or the S1 sink.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 14. Next Safe Step

- A **separately-authorized docs-only S5 Runner Planning Charter** — conceptually planning the runner/orchestration
  that wires reader → S2 → {B4 | S4} → S1 and routes **both** equal-peer families (score + halt), still designing no
  runtime, no storage, and no actionability. It is docs-first and separately gated.
- Independently/subsequently: the **S1 storage-medium** charter (inheriting the ratified S1 interface) and the
  **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The S5 runner, the storage medium, durable persistence, the
  Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the S4 halt-materialization runtime is **BUILT + RATIFIED** at `3851803` (strict 2-file slice; S4
**22/22**, both full lock files green with no lock edit, upstream **89 passed**, zero regressions, no broad pytest) —
a **pure, stateless, deterministic** `materialize_passive_halt_record` that packages **one already-observed**
structural halt carrier (`OptionBLocalParseHalt` / `B3PassiveClientWiringError` / `BlockedPacket`; none invented)
plus the **existing** `S2IdentityWiringCandidate` into **one** `ObservationHaltRecord` admitted by the **real** S1
reference sink, under **exact-type admission** (no `isinstance`; subclasses rejected), **zero object inspection**
(carrier carried opaquely by reference; no attribute access / `str` / `repr` / traceback / message parsing), a
**static type-keyed descriptor** (type provenance, not severity/taxonomy/identity, content-independent), the
**Absolute None Mandate** (`opaque_upstream_context = None`, `provenance_timestamp = None` — intentional, not TODOs),
**strict identity discipline** (exact candidate only; no fallback/minted identity), a **closed three-field payload**,
**Zero-Knowledge Transport** of `halt_origin_reference` (binding future consumers), and the **Mortician Rule** (no
retry/repair/normalize/enrich/severity/taxonomy/route/readiness/verdict/execution/actionability/S5 logic). **S4 ≠ S1
sink** — it produces, S1 records. The **halt path is green and equal-peer to the B4 score path**, but **Phase 6.1
remains incomplete**: the **S5 runner**, the **S1 durable storage medium**, and **Cell-3** remain **separately
gated**, and **Phase 6.2 is not ready**. **No executable work is authorized.**
