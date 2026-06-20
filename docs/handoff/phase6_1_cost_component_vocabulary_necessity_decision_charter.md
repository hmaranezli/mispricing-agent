# Phase 6.1 Cost-Component Vocabulary Necessity Decision Charter

> **This is a docs-only decision charter.** It decides exactly one thing — **whether a closed
> `cost_component_type` vocabulary is *necessary* for Phase 6.1 / Master B3 to proceed** — given the evidence
> that Phase 5 net-edge math operates on signed decimal magnitudes and does **not** semantically consume the
> label. It authorizes NO runtime, NO tests, NO lock-test edits, NO Phase 5 runtime amendment, NO B2
> runtime/schema/carrier amendment, NO Master B3 wiring, NO Phase 5 integration, NO B4 scoring, NO durable logs,
> NO `edge_direction`, NO `staleness_threshold_ms`, NO Shadow Intent, NO capacity activation, NO Phase 6.2 work,
> NO pytest, NO graphify. **It defines no vocabulary values and designs no carrier/runtime.** It is subordinate
> to `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md`,
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md`,
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_decision_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `752469968fc7bb72424cd7ac548a1adba555ae3d`

---

## 1. Base / Dependency Chain

**Base commit:** `752469968fc7bb72424cd7ac548a1adba555ae3d`.

References:

- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md` — attempted to ratify the closed
  value set and returned **BLOCKED**; flagged the **necessity question** (its §8/§13) as the next thing to
  resolve.
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md` — ratified
  **owner = Phase 5** and **mechanism = M3** (authoritative doc ratifies the closed set first → later runtime
  lock).
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_decision_charter.md` — framed the ownership/closure
  decision and the total value-space ban.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — ratified mapping cells 1/2/4/5; kept
  **Cell 3 (cost-component vocabulary) BLOCKED**.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — places the cost-vocabulary unblock on the Master-B3
  critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Necessity Decision Exists

The values charter proved that no closed `cost_component_type` set can be ratified from current evidence, and —
in the course of that sweep — surfaced a prior, more fundamental question that the value-ratification track had
silently assumed away: **is a closed, semantically-consumed cost-type vocabulary needed at all for Phase 6.1?**

The whole cost-vocabulary chain (decision → ownership/mechanism → values) was predicated on the premise that
Master B3 must populate a *meaningful* `cost_component_type` and therefore a closed domain must exist first. But
the consumer evidence (§5) shows Phase 5 net-edge economics ride entirely on **signed decimal magnitudes**, and
the label is never read for math or control flow. If that premise is false, the values-charter BLOCK is not a
gap to be filled but a **non-requirement** for Phase 6.1 — and the Master-B3 critical path may not actually
depend on closing the set. This charter decides necessity **before** any further attempt to ratify values, so
the question is governed rather than assumed in either direction.

This charter decides **necessity only**. It does **not** define values, does **not** reverse the ratified
owner/mechanism, and does **not** authorize any carrier or wiring.

---

## 3. Evidence Inventory Inspected (read-only)

- **Phase 5 net-edge calculator** (`phase5/net_edge_calculator_boundary.py`): a whole-file sweep finds **zero**
  occurrences of `cost_component_type`. The calculator computes `net_edge = gross_edge − Σ cost_i` over
  **signed canonical decimal magnitudes**; it validates `gross_edge_value` / `total_cost_value` /
  `net_edge_value` as canonical decimals and **never reads, branches on, or interprets** the cost-type label.
- **Phase 5 cost-friction factory** (`phase5/observable_cost_friction_boundary.py`): `cost_component_type` is a
  closed-record field validated **only** as an exact non-empty, non-whitespace `str`; it is stored on the
  frozen record and surfaced **only in `__repr__`**. No allowed-set / enum / `frozenset` / `in {...}` / `== ".."`
  constraint exists on the field. It is carried verbatim, not consumed.
- **Phase 5 source-result adapter** (`phase5/observable_cost_source_result_adapter.py`): `cost_component_type`
  is a closed-record field, surfaced **only in `__repr__`**, and threaded through verbatim
  (`cost_component_type=result.cost_component_type`) with no validation beyond non-emptiness and no branching.
- **B2 normalization contract** (`phase6_1/b2_normalization_contract.py`): carries **no** `cost_component_type`
  / `cost_component_reference` field. The only cost-related carriers are `binding_role ∈ {GROSS_EDGE, COST}`
  and the optional carrier-only `zero_cost_evidence`. There is **no** B2 cost-type carrier today.
- **Tests:** the only `cost_component_type` literals are `TAKER_FEE` / `MAKER_REBATE` — **test fixtures**, not a
  runtime contract (carried from prior charters; not promoted here).
- **B3 mapping-extraction status:** Cell 3 (cost-component vocabulary) is the **only** still-BLOCKED mapping
  cell (1/2/4/5 ratified); it is blocked precisely *because* a closed vocabulary was assumed necessary and none
  exists.

---

## 4. Summary of Prior Ratified State (carried forward, unchanged)

- **Owner — RATIFIED:** Phase 5 owns the right/duty to close `cost_component_type` (architectural + by-
  elimination; B2 carrier-only, B3 router-only).
- **Mechanism — RATIFIED:** **M3** — an authoritative document ratifies the closed set first, then a later,
  separately-authorized Phase 5 runtime slice locks/enforces it (M4 open free-form rejected as a *policy*).
- **Values — BLOCKED:** no authoritative closed value set is defensible; fixtures are weak/non-authoritative;
  net-edge planning's `BPS`/`RATE`/`PERCENT` is a **unit/scale** vocabulary, not cost-type values.

This charter does **not** touch any of the above. In particular it **cannot** and **does not** reverse owner or
mechanism (see §7, Lock 3).

---

## 5. Net-Edge Consumption Analysis

**Does `cost_component_type` affect Phase 5 math or control flow?** No — on the current repo evidence.

- **Math:** net edge is `gross_edge − Σ cost_i` over signed decimal magnitudes. The arithmetic reads only the
  signed magnitude fields. Whether a cost is a fee or a rebate is expressed by the **sign of the magnitude**
  (negative magnitude = credit/rebate), **not** by the `cost_component_type` label. The calculator contains no
  reference to the label at all.
- **Control flow:** no Phase 5 component branches, gates, routes, sizes, scores, or makes any decision on the
  value of `cost_component_type`. The factory and adapter validate it only as a non-empty string and surface it
  only in `__repr__`.
- **Identity / provenance:** the label participates only as a **carried provenance descriptor** on the closed
  cost record — it labels *what kind of cost this magnitude represents* for human/audit readability, while the
  economics are fully determined by the signed magnitude.

**Conclusion:** on current evidence `cost_component_type` is, behaviorally, **passive provenance metadata**. No
closed domain is required for the net-edge math to be correct or for any existing Phase 5 control flow to
function.

---

## 6. Necessity Decision — **B. CLOSED_VOCAB_NOT_NECESSARY_FOR_PHASE_6_1**

**A closed `cost_component_type` vocabulary is NOT necessary for Phase 6.1 / Master B3 to proceed.**

For Phase 6.1, `cost_component_type` may remain **passive provenance metadata**: an exact non-empty string,
carried verbatim, whose economic meaning is carried **entirely by the signed decimal magnitude**. The repo
evidence (§5) shows no math and no control flow depends on the label, so requiring a closed domain *before* B2
carrier or Master B3 work would be gating the critical path on a contract that nothing currently consumes.

This decision is **scoped to Phase 6.1**. It does **not** assert that a closed vocabulary will never be
desirable; it asserts only that closure is **not a precondition** for Phase 6.1 / Master B3. Any future closure
remains governed by the ratified owner (Phase 5) and mechanism (M3) — see §7, Lock 3.

> Note: choosing B does **not** unblock or authorize a B2 carrier or Master B3 mapping by itself (see §9/§10).
> It removes the *closed-vocabulary precondition*; it does not design or authorize the passive-carrier path. A
> separate charter is still required to authorize any carrier/wiring, even in passive form.

---

## 7. Passive-Provenance Contract and Red-Team Locks (binding under Decision B)

If and when a passive cost-type carrier/route is later separately authorized, it is bound by the following.
These locks are stated now as the **constraints of Decision B**; they authorize nothing executable themselves.

1. **Passive provenance definition.** `cost_component_type` must **never** be used for control flow, branching,
   scoring, routing, `edge_direction`, sizing, execution, allocation, or any math. It is a descriptive string
   only.
2. **Signed-magnitude rule.** Cost economics live **entirely** in the signed decimal magnitude. The label does
   **not** imply fee/rebate polarity or any arithmetic behavior; polarity is the **sign of the magnitude**, not
   the label.
3. **No M3 reversal.** Phase 5 remains the owner and **M3 remains valid**. Phase 5 is only choosing **not to
   close** the vocabulary *for Phase 6.1*. Any future closure must still proceed under M3 (authoritative
   values charter → later Phase 5 runtime lock). This charter does **not** weaken, replace, or pre-empt M3.
4. **Router-only B3.** If later authorized, Master B3 may only **carry/route** the label verbatim. It must
   **never** parse, validate, infer, coerce, normalize, default, or branch on it (no
   `normalized_field_name → cost_component_type` derivation).
5. **B2 carrier implication.** If a future B2 cost-type carrier is authorized, it is **passive string
   provenance only** — never an enum / closed-set validator — **unless** a later M3 values charter ratifies a
   closed set and a separate slice enforces it.
6. **No fallback semantics.** Keeping the field open/passive does **not** authorize `OTHER` / `UNKNOWN` /
   `UNSPECIFIED` / `MISC` / catch-all semantics. An unclear label remains a verbatim provenance string; it is
   **not** a semantic bucket and carries no default meaning.
7. **Scope isolation.** This charter does **not** address `edge_direction`, `staleness_threshold_ms`, Shadow
   Intent, capacity, the live adapter, B4 scoring, durable logs, or Phase 6.2. Those remain separate,
   separately-gated concerns.

---

## 8. If A/C — Exact Future Proof Required (not selected)

Recorded for completeness; **not** the chosen verdict.

- **Had the verdict been A (CLOSED_VOCAB_NECESSARY):** a future, separately authorized step would have had to
  produce, under M3, (1) an authoritative closed allowed-set ratified from a Phase 5 source (not fixtures);
  (2) fail-fast out-of-set semantics; (3) the demonstrated *consumer* that requires the closed domain (a Phase 5
  component that branches/computes on the label) — which the current evidence does **not** exhibit.
- **Had the verdict been C (DEFERRED):** a future read-only step would have had to identify a concrete
  consumer or requirement (e.g. a planned Phase 5 amendment, a B4 scoring need, or a downstream contract) that
  makes the label semantically load-bearing, before necessity could be decided either way.

Neither path is taken: the evidence is sufficient to decide **B**.

---

## 9. Effect on B2 Cost-Type Carrier Status

- The **closed-vocabulary precondition** on a B2 cost-type carrier is **removed** for Phase 6.1: a carrier, if
  later chartered, no longer must wait for a ratified closed set.
- **However, no B2 carrier is unblocked, authorized, designed, named, or typed by this charter.** A passive
  cost-type carrier still requires its **own** separate amendment charter, and even then must be **passive
  string provenance only** (§7, Lock 5), proven supplied by the artifact and never derived from
  `normalized_field_name` / `source_field` / unit / magnitude / position.
- Net status: B2 cost-type carrier is **no longer blocked *on vocabulary closure*, but remains UNBUILT and
  separately-gated** (no design exists; passive-only if ever authorized).

---

## 10. Effect on Master B3 Blocked / Unblocked Status

- **Master B3 is NOT unblocked by this charter.** Decision B removes one blocker on Cell 3 — the demand that a
  closed `cost_component_type` vocabulary exist first — by reframing the label as passive provenance. But:
  - Cell 3 still has **no authorized carrier/route**: a passive pass-through must be separately chartered under
    the router-only lock (§7, Lock 4) before any wiring.
  - The separate Master-B3 blockers **`edge_direction`** (deferred to the Shadow Intent Envelope track) and
    **`staleness_threshold_ms`** remain **untouched and out of scope** here.
- Net status: Master B3 wiring **remains BLOCKED**; this charter only converts the Cell-3 cost-type sub-blocker
  from *"needs a closed vocabulary"* into *"needs a separately-authorized passive carrier/route charter"*,
  while the other Master-B3 blockers stand.

---

## 11. Still-Forbidden Work

- **No** vocabulary values defined, proposed, or endorsed; **no** fixture/prose promotion; **no** fallback
  value.
- **No** Phase 5 runtime amendment (no validation, no closed-set, no factory change).
- **No** B2 carrier field designed, named, typed, or implemented; **no** B2 schema/runtime change.
- **No** Master B3 runtime/design/wiring; **no** Phase 5 integration; **no** parsing/casting/normalizing/
  bridging; **no** B4 scoring; **no** durable logs; **no** output carrier; **no** Shadow Intent; **no** live
  adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.
- **No** reversal or weakening of the ratified owner (Phase 5) or mechanism (M3).

---

## 12. Next Safe Step

- A **separate review** to decide whether to authorize a **docs-only passive cost-type carrier/route charter**
  — under the §7 locks (passive provenance, router-only B3, no closed-set validation) — that would, for the
  first time, define how (and whether) a verbatim `cost_component_type` string is carried B2 → B3 → Phase 5
  without closing the vocabulary. That charter, if authorized, would still design no enum and enforce no set.
- Independently, the separate Master-B3 blockers **`edge_direction`** and **`staleness_threshold_ms`** each
  require their own separately-authorized resolution before Master B3 wiring can proceed.
- **No implementation is authorized by this charter.** Phase 5 vocabulary runtime (if ever needed, under M3),
  any B2 carrier, Master B3 wiring, B4 scoring, durable logs, the live adapter, Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
