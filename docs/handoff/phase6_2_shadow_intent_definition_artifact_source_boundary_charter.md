# Phase 6.2 — Shadow Intent Definition Artifact Source Boundary Charter

> **This is a docs-only source-boundary charter.** It pins **where the declared counterfactual scenario
> definitions come from**, their authority, durability class, seal lifecycle, the deterministic two-input replay
> relationship, and a **targeted** correction of the prior S1-only clauses — for a **future** Phase 6.2 capability.
> It **implements nothing and authorizes nothing executable**: no runtime code, no tests, no test execution, no
> lock-test edits, no frozen-component edits, no Phase 6.1 edits, no S1-adapter edits, no schema implementation, no
> loader, no manifest-writing tool, no Phase 6.2 runtime, no pytest, no graphify. It makes **no** Phase 6.2
> runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_multi_event_context_supply_shadow_state_boundary_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_lifecycle_state_transition_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_field_shape_charter.md`,
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern **except** for the narrow, explicitly-mapped clause
> supersessions in §11.

**Base:** `999a1093a970213f70332f2ce46235a66febdf04`

---

## 1. Base / Purpose

**Base commit:** `999a1093a970213f70332f2ce46235a66febdf04`.

The Evidence-Intersection Classification Predicate inspection (against base `999a109`) proved a hard blocker: the
required predicate references — a per-intent **directional orientation**, a **passive boundary** level distinct from
the observed magnitude, and a **hypothetical-window** horizon — are **NOT present in, and NOT derivable from,**
ratified S1 audit evidence (the passive carriers deliberately strip `edge_direction`; the only audited time field is
`provenance_timestamp`; no window/horizon field exists anywhere). Fabricating them inside S1 evidence is forbidden
(CLAUDE.md rule 3; `999a109` §11).

This charter resolves that blocker the **only** admissible way: those values are **declared counterfactual
assumptions**, not observed facts, and therefore must originate from a **separate, sealed, versioned, durable
scenario-definition artifact** fixed **before** replay — never invented inside the audit trail. This charter pins
**only** the source boundary, authority, durability class, seal lifecycle, deterministic two-input replay law,
cardinality, boundary-level failure taxonomy, and the targeted supersession map. It pins **no** field shapes, types,
encodings, formats, engines, digests, or runtime container types — those are deferred to a later field-shape /
canonical-encoding charter (§15).

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Semantic Classification of the Artifact (binding)

The source is defined **strictly** as a **sealed, versioned, durable scenario-definition artifact**:

- it is **evidence that a specific counterfactual scenario was declared and frozen** — a record that "someone/some
  process *declared* this hypothetical orientation / boundary / window for this Silver pair, and froze it";
- it is **NOT** observed market evidence, **NOT** an S1 observation, **NOT** an audit record, and **MUST NOT** be
  represented, logged, replayed, or projected as if the orientation, boundary, or window were **observed facts**.
  They are **declared assumptions** — the counterfactual "what-if," never the "what-happened";
- it carries **no executable instruction**, grants **no actionability**, and asserts **no** market truth,
  profitability, readiness, or fill. It is an inert offline scenario declaration (§12).

The distinction is load-bearing: S1 supplies what was **observed**; the sealed artifact supplies what was
**declared** as the counterfactual frame against which observations are passively classified.

---

## 3. Dual-Layer Source Architecture (binding)

The scenario definitions live in exactly **two layers**, with a single direction of authority:

- **Canonical authority (durable):** exactly **one** durable, sealed scenario-definition artifact, persisted
  **before** replay. This is the **sole source of truth** for declared counterfactual assumptions.
- **Runtime representation (derived):** a **caller-owned, instance-scoped, immutable in-memory projection** derived
  **once** from that exact sealed artifact at initialization (§5, §8).

The in-memory projection is **never** an independent authority, a hidden store, a writable cache, or a second source
of truth — it is a faithful, read-only, frozen mirror of the one sealed artifact, fully reconstructible from it and
from nothing else. **Concrete storage format and concrete in-memory container type remain DEFERRED** to the
field-shape / canonical-encoding charter (§15); this charter fixes the **authority relationship**, not the types.

---

## 4. Explicit Artifact Selection (binding)

Exactly **one** artifact reference MUST be **explicitly supplied** for a replay. **Explicitly FORBIDDEN** selection
mechanisms:

- directory scanning, glob/wildcard discovery, recursive search;
- "latest" / "newest" / most-recent resolution; version-max resolution;
- environment-variable-selected manifests; config-discovered manifests;
- mutable aliases / symlinks / "current" pointers;
- implicit defaults; and **fallback to another artifact** of any kind.

Replay output MUST remain **attributable to the exact sealed artifact used** — the reconstruction is meaningless
unless the one artifact it was computed against is unambiguous and explicit. **No manifest may be silently selected
or substituted**, and no second artifact may be consulted. (The §13 equality-only contingency is **not** a fallback
artifact and may never silently replace a missing/invalid one.)

---

## 5. Initialization and Seal Lifecycle (binding)

The complete artifact MUST be **located, loaded, structurally validated under the future ratified schema, and
sealed** **before the first S1 audit record is consumed**. This boundary is expressed in **replay-order terms, never
wall-clock terms**: "before the first S1 record is read," not "at time T."

Once S1 replay begins, the sealed artifact is **immutable** for the entire replay. **Forbidden** after replay
start:

- **no** manifest addition; **no** mutation; **no** reload; **no** second read; **no** replacement; **no** partial
  refresh; **no** late-binding of any definition.

**Any modification produces a distinct new artifact** (a new version with its own provenance/digest, §6).
**In-place updates are forbidden.** The seal is the guarantee that the declared counterfactual frame is fixed for
the whole deterministic replay (§7).

---

## 6. Version and Provenance Discipline (binding)

The artifact MUST carry **auditable provenance**: **who/what declared** the counterfactual scenario, its **sealed
artifact reference**, and its **version lineage** (how this version relates to prior versions). This is required so
every shadow reconstruction is explainable ("which declared scenario, declared by whom/what, at which version,
produced this") — the constitution's "why" requirement extended to the declared-input side.

- **Exact provenance fields, canonical bytes, digest algorithm, and encoding are DEFERRED** to the field-shape /
  canonical-encoding charter (§15).
- A future **content digest MAY identify** the sealed artifact **for provenance only**.
- The manifest version / digest **MUST NOT** become a **shadow-intent identity**, a **Silver identity**, a **domain
  identity**, an **ordering mechanism**, or a **rowid substitute**. Provenance identifies the *artifact*; it never
  identifies, orders, or keys an *intent* (intent keying stays the opaque Silver pair, §9).

---

## 7. Pure Deterministic Two-Input Model (binding)

The ratified mathematical boundary is:

```
ShadowState =
    Replay(
        FrozenProjection(SealedScenarioDefinitionArtifact),
        OrderedS1AuditRecords
    )
```

- **`OrderedS1AuditRecords`** — S1 remains the **sole source of observed passive audit events**, consumed in
  append order (the ratified minimal append-order replay, `b06d7ed` §5).
- **`FrozenProjection(SealedScenarioDefinitionArtifact)`** — the sealed artifact remains the **sole source of
  declared counterfactual scenario assumptions** (orientation, passive boundary, hypothetical window), fixed before
  consumption.
- There is **NO** second event stream, **NO** temporal merge, **NO** interleaving algorithm, **NO** race, **NO**
  clock synchronization, **NO** timestamp ordering *between the two sources*, and **NO** live update channel. The
  artifact is **fully fixed before ordered S1 consumption begins**; it contributes **zero events** and **zero clock
  ticks** — it is a static frame, not a stream.
- The reconstruction is a **pure function of both fixed inputs**: same artifact + same ordered S1 records ⇒
  bit-identical shadow state, every replay (the determinism of `e9995e7` §3 is preserved and **extended** to two
  fixed inputs, not weakened).

Audited-observation order remains the **sole clock** (`e9995e7` §2 intact): the artifact supplies declared values,
never time.

---

## 8. Caller-Owned Runtime Projection (binding)

The future runtime projection MUST be **caller-owned, instance-scoped, immutable, and reconstructible solely from
the exact sealed artifact**. **Forbidden:**

- module-level mutable state, globals, singletons, static registries, class-level registries;
- hidden caches, memoization across runs, cross-run reuse, process-wide state;
- mutation through aliases / shared references.

The projection's **lifetime is bounded to the replay invocation/context**, not a wall-clock lifetime: it is built at
initialization, used read-only through the replay, and discarded with the replay context. Two replays share nothing
(mirroring the instance-bound discipline of the S1 in-memory sink and the `999a109` §3 isolated container).
**Concrete runtime types remain DEFERRED** (§15).

---

## 9. Silver-Pair Cardinality (binding)

The `999a109` §4 keying is **preserved**: shadow state is keyed **only** by the ratified opaque Silver pair
`(artifact_locator, physical_record_position)` as recorded in the S1 audit envelope. Against that keying, the sealed
artifact's scenario definitions obey:

- each **qualifying** opaque Silver pair may correspond to **zero or at most one** scenario definition;
- a **missing** definition for a Silver pair is **valid** and produces **no shadow intent** (zero, not an error,
  not a synthetic default);
- **multiple definitions for one Silver pair make the artifact INVALID at pre-flight** (§10) — duplicates are a
  hard pre-flight failure, never a "pick one" / "merge" / "last wins";
- **FORBIDDEN:** sub-identities, ordinals, hashes-of-fields, counters, surrogate intent IDs, and
  rowid-as-domain-identity (the S1 `append_sequence` stays internal append ordering only, `b06d7ed` §6);
- an **unused definition** (one whose Silver pair never appears in the replayed S1 records) MUST **never** fabricate
  an S1 observation or an intent. **Exact unused-definition reporting remains DEFERRED.**

The cardinality is the structural guarantee behind the `999a109` §4 "zero or at most one root intent per qualifying
pair" — now anchored to the declared artifact rather than invented at runtime.

---

## 10. Boundary-Level Error Taxonomy (binding)

Four disjoint, closed bands — none routed back to S4, none written to S1, none attached to a Phase 6.1 DTO:

1. **Pre-flight hard failure** (before **any** S1 record is consumed): the artifact is **absent or unreadable**; the
   artifact is **not sealed**; the artifact **provenance/version reference is invalid** under the future charter; a
   **future-schema structural validation failure**; **duplicate Silver-pair definitions** (§9); or **inability to
   construct one complete immutable projection**. Any of these aborts the replay **before** observation consumption
   — nothing is partially reconstructed.
2. **Valid missing definition** for a Silver pair: **zero intents**, **no failure**, **no synthetic default** (§9).
3. **In-flight unit non-comparability** (a later observation's unit does not match the declared scenario's unit):
   a **passive not-comparable result** — **no lifecycle transition, no mutation, NOT fail-fast, and NOT a Phase 6.1
   halt**. It is an inert "not applicable here" classification, consistent with `999a109` §7 unit-mismatch =
   explicit non-comparability.
4. **Unexpected programmer/runtime errors:** **hard fail-fast**, **never swallowed** and **never converted** into a
   passive classification (the `999a109`/`061bf1b` fail-fast-vs-structural-halt discipline preserved end-to-end).

**Exact malformed-field and scalar parsing rules remain DEFERRED** to the field-shape charter (§15).

---

## 11. Targeted Supersession Map (binding)

This charter supersedes **only** the exact S1-only clauses that conflict with the two-input replay law of §7. It
does **NOT** claim the earlier charters are wholly invalid or wholly replaced — every other provision stands. The
three substituted principles are:

- **(P1)** S1 is the **exclusive observed-event source**;
- **(P2)** the sealed scenario-definition artifact is the **exclusive counterfactual-definition source**;
- **(P3)** shadow reconstruction is a **pure function of both fixed inputs** (§7).

### Section-by-section supersession

| Charter / § | Exact superseded clause (quoted) | Replaced by |
|---|---|---|
| `e9995e7` §2 | "A 'window lapse' / 'expiry' is determined **only** from **audited evidence** … lies beyond the intent's **already-recorded** hypothetical window" | Expiry is classified from the audited S1 **later-observation** `provenance_timestamp` (P1) compared against the **artifact-declared** hypothetical window (P2); the no-wall-clock / freeze-on-stop rule of §2 is **unchanged**. |
| `e9995e7` §3 | "the lifecycle is a **pure function of the audited observation sequence**" | The lifecycle is a pure function of **both** `FrozenProjection(SealedScenarioDefinitionArtifact)` **and** `OrderedS1AuditRecords` (P3); determinism/idempotency **strengthened**, not weakened. |
| `e9995e7` §4 | "classified **only** from already-recorded audited evidence (§2)" | Classified from already-recorded audited S1 evidence (P1) **intersected with** the artifact-declared orientation/boundary/window (P2). |
| `999a109` §7 | "Both operands are **already-recorded audited values read verbatim from S1**; the 'passive boundary' is the intent's **own already-recorded** hypothetical reference" | The **audited-evidence operand** stays read verbatim from S1 (P1); the **passive boundary** and the **orientation** are **declared values from the sealed artifact** (P2), never invented in or read from S1 evidence. |
| `999a109` §8 | "the difference between an intent's **already-recorded** hypothetical-window reference timestamp and a later **replayed** observation's **already-recorded** `provenance_timestamp`, **both read verbatim from S1**" | The **later-observation** `provenance_timestamp` stays from S1 (P1); the **hypothetical-window reference** is a **declared value from the sealed artifact** (P2). `TIMESTAMP_DELTA` exact integer semantics and no-wall-clock rule **unchanged**. |
| `999a109` §9 | "the durable, append-only, monotone trail is the **single source of truth**" | The S1 trail is the single source of truth **for observed events** (P1); the sealed artifact is the single source of truth **for declared counterfactual assumptions** (P2). |
| `999a109` §9 | "per-intent state is **derived from the S1 audit replay**" | Per-intent state is derived from **both** fixed inputs per the §7 law (P3); S1 stays the exclusive **observed-event** source and the no-synthetic-bypass / minimal-append-order-replay rules of §9 are **unchanged**. |

### Explicitly preserved (NOT superseded)

`e9995e7` §2 no-clock/no-timer/no-poll + **freeze-on-replay-stop** + replay-as-sole-clock; §4 transition table +
monotone/absorbing terminals; §5 tombstoned vocabulary; §6 `HYPOTHETICAL_OUTCOME` firewall; §7 S1 read-only (no
write-back, no Phase 6.1 mutation); §8 quarantine + capacity + integration ban. `999a109` §2 **terminal correction
(at most one terminal; open frozen at replay EOF = valid audit state)**; §3 isolated container; §4 deterministic
Silver-pair keying; §5 anti-global-state; §6 passive vocabulary; §7 unit-mismatch = explicit non-comparability +
counterfactual-only / no-outcome-threshold-smuggling; §9 minimal append-order replay + no-synthetic-S1-bypass; §10
capacity/integration ban; §11 no semantic smuggling. All Phase 6.1 closeouts and `CLAUDE.md` stand intact.

**The targeted clauses were identified unambiguously** (exact quotes above); the §11 STOP condition is **not**
triggered.

---

## 12. Anti-Actionability Seal (binding)

The artifact is for **offline counterfactual replay only**. It **MUST NOT** contain or introduce: endpoints,
credentials, account identifiers, broker/exchange connections, callbacks, emission hooks, executable instructions,
quantities, allocations, route choices, live flags, or production-risk controls. It **cannot authorize** live,
paper, canary, execution, routing, emission, or actionability. **Capacity remains DEFERRED with exactly 0 emit
sites.** **Phase 6.1 remains frozen, COMPLETE + RATIFIED.** DRY_RUN and all constitution guardrails remain fully in
force.

---

## 13. Equality-Only Fallback (recorded, NOT activated)

A **unit-matched equality-only intersection** (`EVIDENCE_INTERSECTION` only, per `999a109` §6 — the one comparison
provably constructible without orientation/boundary/window) is **recorded here as an eligible degraded
contingency** for the case where the direction-aware crossing or expiry inputs cannot later be proven/declared.

- This charter does **NOT** activate, implement, or claim this fallback.
- **Activation requires a separately-authorized narrowing charter.**
- The fallback **MUST never silently replace a missing or invalid manifest** (a missing/invalid artifact is a §10
  pre-flight hard failure or a §9 valid-zero-intent, never a silent downgrade to equality-only).

---

## 14. Precise Post-Charter State (ratified)

- **Phase 6.2: UNBUILT and NOT runtime-ready.** This charter pins **only**: the durable **source authority** (§2,
  §3, §6), the **seal lifecycle** (§4, §5), the **frozen runtime-projection boundary** (§3, §8), the **deterministic
  two-input replay law** (§7), **cardinality** (§9), **boundary-level failures** (§10), and the **targeted
  supersession** (§11).
- **Still unbuilt and unauthorized:** the exact artifact **field shape**; **provenance fields**;
  **orientation / boundary / window types**; **canonical encoding and digest**; the **storage / loader runtime**;
  the **predicate implementation**; the **state machine**; the **container runtime**; and **any executable
  integration**.
- **Phase 6.1:** COMPLETE + RATIFIED (frozen, unchanged). **Capacity:** deferred (0 emit sites). **Production /
  live / paper / canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (unchanged from `999a109` §2):** at most one terminal per intent; open frozen non-terminal
  state at replay EOF is valid audit state.

---

## 15. Next Safe Gate

The boundary evidence (source authority, seal lifecycle, two-input law, and supersession are pinned, but the exact
artifact contents are still entirely abstract) shows the next gate is the **field-shape / canonical-encoding
design**, not implementation:

- A **separately-authorized Phase 6.2 Shadow Intent Definition Artifact Field-Shape & Canonical-Encoding Charter** —
  a docs-only design that must **prove and pin**: the exact fields/types/units; the Silver-pair linkage; the
  declared **orientation**; the declared **passive boundary**; the **hypothetical window** semantics; the
  **provenance / version** references; the **durable encoding**; the **content digest**; and the **exact validation
  rules** (malformed-field, scalar parsing, exact decimal / exact integer discipline).
- **No runtime TDD becomes eligible from this boundary charter alone.** Only after that field-shape / encoding
  charter (and the resulting closed, proven predicate contract) may a separately-authorized Phase 6.2 shadow-intent
  reconstruction runtime / state-machine / container / loader TDD slice be considered. **This charter does NOT open,
  draft, or perform that step.**

**Conclusion:** the prior Evidence-Intersection blocker (orientation / boundary / window absent from S1 evidence) is
resolved structurally — those are **declared counterfactual assumptions**, sourced from a **sealed, versioned,
durable scenario-definition artifact** (evidence that a scenario was *declared and frozen*, **never** observed
market fact, **never** an S1 observation, **never** actionable), **explicitly selected** (one artifact, no scan /
latest / env / alias / fallback), **located-loaded-validated-sealed before the first S1 record** and then immutable
(any change = a new artifact; in-place updates forbidden), with **auditable provenance / version lineage** (exact
fields + digest deferred; version/digest never an intent/Silver/domain identity or ordering). Shadow reconstruction
is ratified as the **pure two-input function** `ShadowState = Replay(FrozenProjection(SealedScenarioDefinition
Artifact), OrderedS1AuditRecords)` — **no second event stream, no temporal merge, no interleave, no inter-source
clock**, the artifact fully fixed before ordered S1 consumption — with a **caller-owned, instance-scoped, immutable,
replay-context-bounded** projection (no globals / singletons / caches / cross-run reuse). **Silver-pair cardinality**
holds (zero-or-one definition per qualifying pair; missing = zero intents; duplicates = pre-flight invalid; no
surrogate IDs / rowid identity; unused definitions fabricate nothing). The **boundary-level error taxonomy** is
closed (pre-flight hard-fail; valid-missing = zero; in-flight unit non-comparability = passive no-op, not a halt;
unexpected errors = fail-fast; nothing routed to S4 / written to S1 / attached to a Phase 6.1 DTO). The **targeted
supersession map** (§11) replaces **only** the quoted S1-only clauses of `e9995e7` §2/§3/§4 and `999a109` §7/§8/§9
with the two-source law, **preserving** every lifecycle / quarantine / pass-halt / terminal / capacity / no-clock /
no-actionability / no-production provision. An **equality-only fallback** is recorded but **not activated** (needs a
separate narrowing charter; never a silent manifest replacement). The artifact is **offline-replay-only** and
carries **no** endpoint / credential / connection / callback / emission / instruction / quantity / route / live
flag; **capacity stays deferred at 0 emit sites**; **Phase 6.1 stays frozen, COMPLETE + RATIFIED**. **Phase 6.2
remains UNBUILT and NOT runtime-ready**; the **only** next safe step is a separately-authorized **Phase 6.2 Shadow
Intent Definition Artifact Field-Shape & Canonical-Encoding Charter**, **not opened here**. **No executable work is
authorized.**
