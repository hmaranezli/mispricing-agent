# Phase 6.2 — Source-Authority & Determinism Targeted Amendment Charter

> **This is a docs-only corrective amendment charter.** It repairs **only** the residual normative contradictions
> and premature determinism/fallback claims left after the source-boundary charter (`07135be`) introduced the
> two-authority model — it does **NOT** redesign the accepted dual-layer boundary. It **implements nothing and
> authorizes nothing executable**: no runtime code, no tests, no test execution, no lock-test edits, no
> frozen-component edits, no Phase 6.1 edits, no S1-adapter edits, no schema/field/encoding/digest definitions, no
> loader, no Phase 6.2 runtime, no pytest, no graphify. It **edits no previous charter file**; it corrects them
> **only** through the exact, explicit supersession map in §12. It makes **no** Phase 6.2 runtime/paper/live/
> production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_source_boundary_charter.md`,
> `docs/handoff/phase6_2_multi_event_context_supply_shadow_state_boundary_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_lifecycle_state_transition_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_field_shape_charter.md`,
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern **except** for the narrow, explicitly-mapped clause
> supersessions in §12.

**Base:** `07135beaae505206fcb2bd8ed7c721f9f2106583`

---

## 1. Base / Purpose

**Base commit:** `07135beaae505206fcb2bd8ed7c721f9f2106583`.

`07135be` correctly introduced the two-authority model (S1 = observed events; sealed scenario-definition artifact =
declared counterfactual assumptions) and the two-input replay law, and mapped the `e9995e7`/`999a109` S1-only
supersessions. But three earlier charters (`a9ed9f4`, `ef26f59`) still carry **S1-exclusive** derivation,
trust-boundary, and determinism language that now contradicts the ratified two-input law, and `07135be` itself
**over-claims** determinism (`bit-identical`), **over-asserts** the equality-only fallback (`provably
constructible`), and **prematurely combines** two future design gates. This amendment **repairs only those exact
omissions/overclaims** through a section-by-section supersession map. The accepted dual-layer boundary is **preserved
intact** (§3); nothing is redesigned.

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Evidence-First Clause Inspection (the exact conflicting clauses, quoted)

All target clauses were located and quoted **unambiguously**; the inspection STOP condition is **not** triggered.

- **`a9ed9f4` §3** — "A shadow intent is a **diagnostic artifact** computed from already-recorded passive
  observations; it is inert."
- **`a9ed9f4` §5** — "Phase 6.2 state reconstruction **MUST** flow through the ratified **S1 SQLite/WAL audit
  trail** boundary — the durable, append-only, monotonic record is the **single source of truth** for 'what was
  observed.'"; "shadow-intent state is **derived from the S1 audit replay** (append-order readback), never from live
  recomputation or a parallel hidden store"; "Mitigation: **S1-replay-only reconstruction** + determinism checks
  (§9)."
- **`a9ed9f4` §9 item 4** — "**Replay determinism** — reconstructing identical shadow state from the same S1 audit
  trail must be **byte/shape deterministic** (the durable payload is already deterministic, fixed-key canonical
  text)."
- **`a9ed9f4` §9 item 5** — "**Idempotency** — replaying the same audited events any number of times yields the same
  state; no double-counting, no accumulation drift."
- **`ef26f59` §5** — "The shadow-intent shape and its future state transitions are **derived through the ratified S1
  SQLite/WAL audit replay boundary** — the append-only durable trail is the **single source of truth**."
- **`07135be` §7** — "same artifact + same ordered S1 records ⇒ **bit-identical shadow state**, every replay".
- **`07135be` §11** — "**(P3)** shadow reconstruction is a **pure function of both fixed inputs** (§7)." (correct;
  **preserved/affirmed**, not superseded — quoted per inspection requirement.)
- **`07135be` §13** — "(`EVIDENCE_INTERSECTION` only, per `999a109` §6 — the one comparison **provably
  constructible** without orientation/boundary/window)".
- **`07135be` §15** — "A **separately-authorized Phase 6.2 Shadow Intent Definition Artifact Field-Shape &
  Canonical-Encoding Charter**".

---

## 3. Preserved Architecture (ratified, NOT reopened)

`07135be`'s boundary design **remains valid and is NOT reopened or redesigned**. Specifically ratified-as-is:

- the **sealed, versioned, durable scenario-definition artifact** as the declared-assumption authority;
- the **immutable, caller-owned, instance-scoped runtime projection**;
- **no second event stream**; **no temporal merge** or **inter-source clock**;
- **Silver-pair 0..1 cardinality** (zero-or-one definition per qualifying pair; missing = zero intents);
- **pre-flight sealing** (artifact fixed before the first S1 record);
- **anti-global-state**; **capacity at exactly 0 emit sites**; **Phase 6.1 quarantine**;
- **no live / paper / canary / execution / routing / actionability**.

This amendment touches **none** of these; it repairs only source-authority wording, determinism overclaims, the
fallback overclaim, and the gate split.

---

## 4. Corrected Source-Authority Law (binding)

The exact two-authority model:

- **S1 is the EXCLUSIVE source of observed factual events:** `SCORE`, `HALT`, observed values, units, provenance
  timestamps, and the opaque Silver audit references.
- **The sealed scenario-definition artifact is the EXCLUSIVE source of declared counterfactual assumptions:**
  orientation, passive boundary, and the hypothetical-window declaration.
- The artifact is **NOT** observed market evidence and **NOT** an S1 observation.
- **S1 MUST NOT** contain or manufacture scenario assumptions.
- **The artifact MUST NOT** contain, manufacture, replace, or override observed S1 events.
- **Shadow reconstruction is a pure function of both fixed inputs.**

**One explicitly selected sealed artifact is required for a replay.** Individual Silver pairs may still have **zero**
definitions; a **missing definition remains valid and produces zero intents** (`07135be` §9 preserved).

---

## 5. Supersession of `a9ed9f4` §3 (binding)

The clause "A shadow intent is a **diagnostic artifact** computed from already-recorded passive observations" is
**superseded** by:

> **A shadow intent is reconstructed from observed S1 evidence evaluated within one explicitly selected, sealed
> counterfactual scenario-definition frame.**

**Preserved unchanged** from `a9ed9f4` §3: the inert **diagnostic status**; **no actionability**; the **DRY_RUN**
posture; and **no execution, routing, sizing, allocation, or integration**. The entire MUST-NOT list of §3 (no
exchange/market-data/venue API, no paper-broker, no order routing/emission/execution, no live actionability/trade
trigger/sizing surface, no production integration) stands intact.

---

## 6. Supersession of `a9ed9f4` §5 (binding)

The S1-only trust-boundary language ("the durable, append-only, monotonic record is the **single source of truth**
for 'what was observed'"; "shadow-intent state is **derived from the S1 audit replay** … never from … a parallel
hidden store"; "**S1-replay-only reconstruction**") is **corrected** to the two-authority trust boundary:

- **S1 remains the single source of truth for what was OBSERVED.**
- **The sealed artifact is the single source of truth for what counterfactual scenario was DECLARED.**
- **State reconstruction consumes BOTH fixed inputs.**
- **"Non-S1 side-channel" remains forbidden** for observed events, for hidden mutable state, for live recomputation,
  and for unratified inputs.
- **The explicitly selected sealed artifact is a RATIFIED replay input, NOT a hidden side channel** — it is the
  declared-assumption authority of §4, fixed at pre-flight, not a parallel observed-event store.
- **Ad-hoc fabrication of observed records OR of scenario definitions remains forbidden.**
- **Minimal append-order S1 replay remains unchanged** (`b06d7ed` §5).

The §5 risk framing (trust-boundary erosion) and the temporary-S1-fixtures allowance stand intact, now read against
both fixed inputs.

---

## 7. Supersession of `ef26f59` §5 (binding)

**Only** the S1-exclusive derivation language of `ef26f59` §5 ("derived through the ratified S1 … boundary — the
append-only durable trail is the **single source of truth**") is **replaced** by:

- **observed evidentiary references remain borrowed from S1** (the opaque Silver identity pair + audited
  append-position, by reference, never minted);
- **declared orientation / boundary / window originate ONLY from the sealed artifact** (never fabricated or
  live-recomputed, never read out of S1 evidence);
- **lifecycle state is reconstructed from the intersection of BOTH fixed inputs**;
- **synthetic observed-event bypass remains forbidden**;
- **no Phase 6.1 mutation or write-back is introduced.**

**Preserved unchanged** from `ef26f59`: all anti-actionability **vocabulary** (§3), the **inert field-shape intent**
(§6), **quarantine** (§7), **capacity** (§8), and every **no-actionability** provision. The borrow-not-mint identity
discipline is unchanged.

---

## 8. Corrected Determinism Language (binding)

**Superseded:** (a) `a9ed9f4` §9 item 4 "byte/shape deterministic … from the same S1 audit trail" (S1-alone basis);
(b) `a9ed9f4` §9 item 5 idempotency "replaying the same audited events" (omits the fixed artifact input); and
(c) `07135be` §7 "**bit-identical shadow state**" wording. All three are **replaced** by:

> **The same sealed artifact and the same ordered S1 audit sequence produce deterministically equivalent logical
> shadow state.**

- **Bit-identical, byte-identical, and canonical serialized identity are NOT yet claimed.**
- Those guarantees **remain DEFERRED** until field shape and canonical encoding are separately ratified (§11 Gate A,
  Gate B).
- **Idempotency is defined over the COMPLETE fixed input pair** (sealed artifact + ordered S1 records), **not S1
  alone** — replaying the same pair any number of times yields the same logical state; no double-counting, no
  accumulation drift.
- **No randomness, wall clock, environment selection, hidden state, or mutable cache may influence logical output.**

`07135be` §7's two-input law and "no second event stream / no temporal merge / no inter-source clock / artifact
fixed before consumption" wording is otherwise intact; only the "bit-identical" overclaim is downgraded to "logical
equivalence" pending encoding ratification.

---

## 9. Clarified Hypothetical-Window Roles (binding)

`07135be`'s ambiguous "window reference from artifact" wording is **clarified into three distinct roles**, **without**
defining any exact field, type, unit, or inequality:

- **Anchor:** the **root / qualifying S1 observation's audited provenance timestamp** (observed, from S1).
- **Declared duration / window:** supplied **only by the sealed artifact** (declared, not observed).
- **Comparison observation:** a **later ordered S1 observation's audited provenance timestamp** (observed, from S1).
- **No** wall clock, `now()`, timer, scheduler, polling, or **artifact-generated event** — the artifact supplies a
  declared duration value, never a clock tick or an event.
- **Exact field names, scalar type, unit token, range, parsing rule, and the expiry inequality remain DEFERRED** to
  the Field-Shape (Gate A) and later Predicate charters.
- **No example duration is introduced and no seconds/milliseconds unit is assumed here.**

Expiry thus reads two **observed** S1 timestamps (anchor, comparison) against one **declared** artifact duration —
resolving the prior blocker (the window is declared, not invented in S1) without pinning any concrete shape.

---

## 10. Corrected Equality-Only Fallback Status (binding)

`07135be` §13's "the one comparison **provably constructible** without orientation/boundary/window" implication is
**superseded**. The unit-matched equality-only intersection is pinned as:

- an **eligible-but-UNPROVEN degraded contingency**;
- with **operand paths and the exact comparability contract still UNPINNED**;
- **NOT activated**;
- **NOT runtime-eligible**;
- **never a silent replacement** for a missing/invalid artifact (a missing/invalid artifact stays a `07135be` §10
  pre-flight hard failure or a §9 valid-zero-intent);
- **requiring a separately-authorized narrowing charter** if ever selected.

"Provably constructible" overstated its readiness: even equality-only requires later-ratified operand paths and a
comparability contract that do not yet exist. It is a **contingency**, not a proven capability.

---

## 11. Split Future Design Gates (binding)

`07135be` §15's combined **"Field-Shape & Canonical-Encoding Charter"** next gate is **superseded** by **two
sequential, separately-authorized docs-only gates**:

**Gate A — Phase 6.2 Shadow Intent Definition Artifact Field-Shape Charter** (eligible next):
- exact fields; exact scalar / container types; units; Silver-pair linkage; orientation; passive boundary; window
  semantics; provenance / version references; closed structural validation rules.
- **NO** storage encoding, canonical bytes, digest algorithm, loader, or runtime.

**Gate B — Phase 6.2 Shadow Intent Definition Artifact Canonical-Encoding & Digest Charter** (eligible **only after
Gate A is ratified**):
- durable format; canonical byte representation; ordering / normalization rules; content digest; artifact-reference
  verification.
- **NO** runtime implementation.

**No runtime TDD becomes eligible from this amendment.** The deferred bit/byte/canonical determinism guarantees of
§8 are resolved across Gate A (shape) then Gate B (encoding/digest), in that order.

---

## 12. Exact Supersession Discipline (binding)

This amendment supersedes **only** the listed clauses; `07135be`'s boundary design remains valid; the
`e9995e7`/`999a109` supersessions already mapped by `07135be` §11 **remain intact**; and **all unlisted Phase 6.1 /
6.2 constraints remain binding**. The earlier charters are **not** wholly invalid or wholly replaced.

| Source / § | Exact quoted clause | Precise replacement | Explicit preserved remainder |
|---|---|---|---|
| `a9ed9f4` §3 | "A shadow intent is a **diagnostic artifact** computed from already-recorded passive observations; it is inert." | "A shadow intent is **reconstructed from observed S1 evidence evaluated within one explicitly selected, sealed counterfactual scenario-definition frame**." (§5) | Inert diagnostic status; no actionability; DRY_RUN; no execution/routing/sizing/allocation/integration; the full §3 MUST-NOT list. |
| `a9ed9f4` §5 | "the durable, append-only, monotonic record is the **single source of truth** for 'what was observed'" + "**derived from the S1 audit replay** … never from … a parallel hidden store" + "**S1-replay-only reconstruction**" | S1 = single source of truth for **observed** events; sealed artifact = single source of truth for **declared** assumptions; reconstruction consumes **both** fixed inputs; the selected sealed artifact is a **ratified input, not a side channel** (§6). | "Non-S1 side-channel" forbidden for observed events/hidden state/live recomputation/unratified inputs; no fabrication of observed records or definitions; minimal append-order S1 replay; temp-fixture allowance; trust-erosion risk framing. |
| `a9ed9f4` §9 item 4 | "reconstructing identical shadow state from the same S1 audit trail must be **byte/shape deterministic** (the durable payload is already deterministic, fixed-key canonical text)" | "The same sealed artifact and the same ordered S1 audit sequence produce **deterministically equivalent logical shadow state**"; bit/byte/canonical identity **deferred** to Gate A→B (§8). | Determinism as a required property (no randomness/clock/env/hidden state/cache); the durable S1 payload's own canonical determinism (`b06d7ed`) unchanged. |
| `a9ed9f4` §9 item 5 | "replaying the **same audited events** any number of times yields the same state; no double-counting, no accumulation drift" | Idempotency defined over the **complete fixed input pair** (sealed artifact + ordered S1 records), not S1 alone (§8). | No double-counting; no accumulation drift; the idempotency requirement itself. |
| `ef26f59` §5 | "**derived through the ratified S1 SQLite/WAL audit replay boundary** — the append-only durable trail is the **single source of truth**" | Observed references borrowed from S1; declared orientation/boundary/window **only** from the sealed artifact; lifecycle state from the **intersection of both** fixed inputs (§7). | Synthetic observed-event bypass forbidden; no Phase 6.1 mutation/write-back; §3 vocabulary; §6 inert field-shape; §7 quarantine; §8 capacity; borrow-not-mint identity; minimal append-order replay. |
| `07135be` §7 | "same artifact + same ordered S1 records ⇒ **bit-identical shadow state**, every replay" | "deterministically **equivalent logical** shadow state"; bit/byte identity **deferred** (§8). | Two-input law; no second event stream/temporal merge/inter-source clock; artifact fixed before consumption; pure function of both inputs; audited order = sole clock. |
| `07135be` §13 | "the one comparison **provably constructible** without orientation/boundary/window" | Equality-only = **eligible-but-unproven** degraded contingency; operand paths + comparability contract **unpinned**; not activated; not runtime-eligible (§10). | Not activated; activation needs a separate narrowing charter; never a silent manifest replacement. |
| `07135be` §15 | "a separately-authorized Phase 6.2 Shadow Intent Definition Artifact **Field-Shape & Canonical-Encoding Charter**" | **Two** sequential gates: **Gate A** Field-Shape, then **Gate B** Canonical-Encoding & Digest (§11). | No runtime TDD eligible; docs-only design path; the deferral of all artifact contents. |

**Affirmed (NOT superseded):** `07135be` §11 (P1)/(P2)/(P3) — "(P3) shadow reconstruction is a **pure function of
both fixed inputs**" is correct and stands. `07135be` §2/§3/§4/§5/§6/§8/§9/§10/§12/§14 stand intact. All
`e9995e7`/`999a109` supersessions mapped by `07135be` §11 remain intact. All Phase 6.1 closeouts and `CLAUDE.md`
stand.

---

## 13. Precise Post-Amendment State (ratified)

- **Documentation contradiction: CLOSED** — every identified clause (`a9ed9f4` §3/§5/§9-4/§9-5; `ef26f59` §5;
  `07135be` §7/§13/§15) is mapped in §12.
- **Phase 6.2: UNBUILT and NOT runtime-ready.**
- **Definition-artifact field shape: UNBUILT.** **Canonical encoding / digest: UNBUILT.**
- **Predicate runtime, loader, state machine, and container runtime: UNBUILT.**
- **Phase 6.1:** frozen, **COMPLETE + RATIFIED**.
- **Capacity:** deferred at exactly **0 emit sites**.
- **Production / live / paper / canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (unchanged):** at most one terminal per intent; open frozen non-terminal state at replay EOF
  is valid audit state.

---

## 14. Next Safe Step

The amendment resolves the wording contradictions but pins **no** artifact contents; the next gate is the
field-shape design **only**:

- **Gate A — Phase 6.2 Shadow Intent Definition Artifact Field-Shape Charter** (docs-only): exact fields, types,
  units, Silver-pair linkage, orientation, passive boundary, window semantics, provenance/version references, and
  closed structural validation rules — **no** storage encoding, canonical bytes, digest, loader, or runtime.
- **Gate B** (Canonical-Encoding & Digest) becomes eligible **only after Gate A is ratified**; it is named here for
  ordering only and is **not** the next step.
- **This amendment does NOT open, draft, or perform Gate A** (or Gate B).

**Conclusion:** the residual S1-exclusive and over-claimed wording is corrected through a **targeted, quote-anchored
supersession map** (§12) and nothing else. The **two-authority law** is pinned (§4): **S1 is the exclusive source of
observed factual events** (SCORE/HALT/values/units/provenance timestamps/Silver references) and **the sealed
scenario-definition artifact is the exclusive source of declared counterfactual assumptions** (orientation / passive
boundary / hypothetical-window declaration); neither manufactures, replaces, or overrides the other; reconstruction
is a **pure function of both fixed inputs**; one explicitly selected sealed artifact is required, while a Silver pair
with **zero** definitions stays valid and yields zero intents. `a9ed9f4` §3 is corrected so a shadow intent is
**reconstructed from observed S1 evidence evaluated within one sealed counterfactual frame** (inert / DRY_RUN /
non-actionable preserved); `a9ed9f4` §5 trust boundary becomes **two-source** (S1 = observed truth, artifact =
declared truth, both consumed; the selected artifact is a ratified input, not a side channel; non-S1 side channels,
hidden state, live recomputation, unratified inputs, and ad-hoc fabrication of records **or** definitions stay
forbidden; minimal append-order replay unchanged); `ef26f59` §5 keeps **observed references borrowed from S1** while
**orientation/boundary/window come only from the artifact**, with lifecycle state reconstructed from **both** (no
synthetic bypass, no Phase 6.1 mutation). Determinism is downgraded from **bit-identical** to **deterministically
equivalent logical shadow state** (`a9ed9f4` §9-4/§9-5 and `07135be` §7), with **byte/canonical identity deferred**
to Gate A→B and **idempotency defined over the full fixed input pair**, free of randomness/clock/env/hidden state/
cache. Hypothetical-window roles are split into **anchor (S1 observed) + declared duration (artifact) + comparison
(S1 observed)** with **no clock/timer/scheduler/poll/artifact-event** and **all exact types/units/inequality
deferred** (no example duration, no assumed unit). The equality-only fallback is downgraded to an
**eligible-but-unproven, unpinned, un-activated** contingency that **never silently replaces** a missing/invalid
artifact and needs a separate narrowing charter. The combined future gate is **split** into sequential **Gate A
(Field-Shape)** then **Gate B (Canonical-Encoding & Digest)**. `07135be`'s boundary design, the `e9995e7`/`999a109`
supersessions it mapped, and **all unlisted Phase 6.1/6.2 constraints remain binding**; **capacity stays deferred at
0 emit sites**; **Phase 6.1 stays frozen, COMPLETE + RATIFIED**. The documentation contradiction is **CLOSED**;
**Phase 6.2 remains UNBUILT and NOT runtime-ready**; the **only** next safe step is the separately-authorized
**Gate A — Phase 6.2 Shadow Intent Definition Artifact Field-Shape Charter**, **not opened here**. **No executable
work is authorized.**
