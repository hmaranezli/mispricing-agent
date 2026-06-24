# Post-Phase 6.2 Cryptographic Wiring & Trust Anchor Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It ratifies **no** runtime action. It defines the boundary that must
  be satisfied **before** any production cryptographic verification wiring or trust-anchor
  provisioning. It **implements nothing**, **wires no verifier**, **creates no trust-anchor file**,
  **creates no DB**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** approval ledger DB creation, **no** S1 access / DB creation /
  append, **no** production stream, **no** S1 evidence matrix construction.
- It reads **no** raw ledger / body / payload; performs **no** private key generation / loading /
  signing / seed handling / GPG / YubiKey / offline-salt implementation; inspects **no** wallet /
  credential / secret / env.
- It selects **no** concrete cryptographic library (any tooling named is a **future-only,
  non-authoritative example**).
- It performs **no** network / API / order-routing / monitoring / tmux / runtime-run interaction,
  **no** paper / dry-run / live / canary, **no** trading / actionability / capacity inference.
- **Core doctrine:** dependency injection that is safe for tests is **not** safe as a production
  trust path; a fingerprint pin is only as strong as its **Day-Zero ceremony**; a verification
  result is **evidence at most**, never authority.
- **Human Approval Package Verification slice: RATIFIED (isolated parsing + passive fail-closed +
  canonical bytes + schema lock + public-key fingerprint mismatch handling only).**
- **Human approval ledger DB: NOT CREATED.**
- **S1 evidence matrix construction: BLOCKED / UNSTARTED.** **S1 append: DENIED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `8016b0f87ebd29f34185a2d9240ae06e0a7b90b0`.
- Parent chain:
  - `8016b0f87ebd29f34185a2d9240ae06e0a7b90b0` = **RATIFIED** Human Approval Package Verification
    TDD slice (`approval/package_verifier.py` + tests).
  - `7d3e7cd0ab2f6e65cc7789f38a306e2806664094` = **RATIFIED** Human Approval Ledger / Operator
    Decision Mechanism TDD Charter.
  - `2d52ed27defa5c4088ab8105adeb6c999c20aa2b` = **RATIFIED** Human Approval Ledger / Operator
    Decision Mechanism Boundary Charter.
- This charter defines the **cryptographic wiring & trust-anchor** boundary, mathematically blocking
  the two remaining Gemini / Codex concerns after the verification slice:
  1. **Dependency-injection / fake-crypto-verifier risk** — an injected callable that is convenient
     in tests must never become a production trust path.
  2. **Day-Zero public-key fingerprint trust-anchor bootstrap risk** — the pinned fingerprint must
     originate from a verifiable offline ceremony, not from the server, network, model, or config.
- It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **trust-anchor / wiring non-authority line**: the ratified slice proves the
  **verification logic** fails closed on parsing, canonical bytes, schema, and fingerprint mismatch
  — but it does **not** prove the production **verifier primitive** is genuine, nor that the **pinned
  fingerprint** is the operator's true key. Those are this charter's concern, and both remain
  **BLOCKED** until separately ratified.
- It exists to make **"injected verifier ⇒ production trust", "fingerprint constant ⇒ trusted
  anchor", and "tests pass ⇒ production readiness" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Charter Boundary

1. This charter creates **no** crypto implementation, **no** verifier wiring, **no** trust-anchor
   file, **no** DB, **no** S1 append, **no** matrix, **no** capacity.
2. It **only** defines the future boundary that must be satisfied before any production cryptographic
   verification wiring.
3. It **authorizes no** runtime, S1 access, trading, paper / canary / live, recovery, routing, or
   capacity.

### Gate B — Current Evidence Basis

- Base commit: `8016b0f87ebd29f34185a2d9240ae06e0a7b90b0`.
- The Human Approval Package Verification slice is **BUILT / TESTED / RATIFIED** only for: **isolated
  parsing**, **passive fail-closed behavior**, **exact canonical bytes**, **closed schema lock**,
  and **public-key fingerprint mismatch handling**.
- The **AST import allowlist** (`json`, `hashlib`, `dataclasses`, `typing`, `__future__` only) is
  **strong isolation evidence, not a mathematical proof of zero attack surface**. It demonstrates no
  forbidden dependency is imported by the slice; it does **not** prove the eventual production
  verifier primitive, runtime wiring, or trust anchor are sound.
- No production verifier primitive, trust anchor, ceremony, rotation, or revocation exists yet.

### Gate C — Production Crypto Verifier Identity Boundary

The future concrete production verifier primitive must:

- be **statically pinned or resolved through a strict allowlist** (no arbitrary lookup);
- **not** be arbitrary runtime injection;
- **not** accept lambda / dummy / mock / always-true callables in production;
- expose **no** private-key / signing primitive;
- perform **public-key-only verification**;
- bind **verifier identity / version / fingerprint / provenance** to deterministic evidence.

Any verifier that is not identity-pinned, version-bound, and provenance-bound **fails closed**.

### Gate D — Test-Double / Mock Firewall

1. Test doubles are allowed **only in test runtime**.
2. A mock verifier, dummy verifier, always-true verifier, monkeypatch verifier, or freely injected
   callable **cannot cross into the production path**.
3. Any production path using a test verifier **fails closed**.
4. Any ambiguous environment flag / config that could select test crypto **fails closed**.
5. **Test convenience must never become production authority.**

### Gate E — Day-Zero Trust Anchor Ceremony

The future trust anchor must be established by an explicit ceremony that defines:

- **offline public-key fingerprint generation**;
- **human-visible fingerprint confirmation**;
- a **one-time provisioning artifact**;
- an **immutable / pinned storage requirement**;
- **independent verification of the pinned fingerprint before first use**;
- **no server self-generation of its own trust anchor**;
- **no network-fetched trust anchor**;
- **no model / agent / log / config as a trust source**;
- **exact fail-closed behavior if ceremony evidence is missing** (no anchor ⇒ no verification ⇒ no
  approval ⇒ no action).

### Gate F — Trust Anchor Rotation / Revocation Boundary

1. Rotation must be a **separate future ceremony**.
2. Revocation must **fail closed**.
3. Multiple active keys require an **explicit future rule**; the default is **deny**.
4. Any mismatch, downgrade, stale key, expired key, missing revocation state, or ambiguous rotation
   state **fails closed**.
5. **No automatic key rollover.**

### Gate G — Fail-Closed Conditions

The following must **fail closed** (at least twenty-four):

1. **arbitrary verifier injection**;
2. **always-true verifier**;
3. **mock verifier in production**;
4. **dummy / lambda verifier in production**;
5. **monkeypatch verifier in production**;
6. **unknown verifier identity**;
7. **unpinned verifier implementation**;
8. **verifier version mismatch**;
9. **verifier provenance missing**;
10. **public key fingerprint mismatch**;
11. **missing day-zero ceremony evidence**;
12. **mutable trust-anchor artifact**;
13. **network-derived trust anchor**;
14. **server-self-generated trust anchor**;
15. **model-derived trust anchor**;
16. **log-derived trust anchor**;
17. **config-derived authorization**;
18. **missing revocation state**;
19. **ambiguous rotation state**;
20. **stale / expired / downgraded key**;
21. **private-key material on VPS**;
22. **signing primitive exposed on VPS**;
23. **S1 append attempted from verification result**;
24. **matrix construction attempted from verification result**;
25. **paper / live / trading / capacity inference attempted from verification result**;
26. **ambiguous environment flag selecting test crypto**.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Non-Authority Rules

Future systems must prove (at least fourteen rules):

- **RATIFIED verification slice ≠ S1 authorization.**
- **valid package verification ≠ S1 append authorization.**
- **public-key fingerprint match ≠ approval-ledger DB creation.**
- **trust-anchor ceremony ≠ capacity.**
- **crypto pass ≠ trading / actionability.**
- **human approval package validity ≠ paper / canary / live permission.**
- **Gemini / Claude / Codex output ≠ operator command.**
- **tests passing ≠ production readiness.**
- **injected verifier ≠ trusted verifier.**
- **fingerprint constant ≠ verified trust anchor.**
- **AST allowlist ≠ zero attack surface proof.**
- **verifier identity pin ≠ append authority.**
- **rotation ceremony ≠ automatic rollover.**
- **capacity remains 0.**

### Gate I — Required Future Command Shape (descriptive only)

A later implementation command, before any crypto wiring can be built, must explicitly state:

- the **exact base SHA**;
- the **exact target module / file**;
- the **exact production verifier primitive identity rule** (static pin / allowlist);
- the **exact trust-anchor artifact shape**;
- the **exact fail-closed tests**;
- an **explicit no-S1 / no-capacity boundary**;
- **explicit targeted tests only**.

This section grants **no** current authority; absent such a command, no crypto wiring is authorized.

### Gate J — No-Auto-Activation Post-State

- Cryptographic Wiring & Trust Anchor Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Human Approval Package Verification slice: **RATIFIED**.
- Human approval ledger DB: **NOT CREATED**.
- Human approval ledger / operator decision mechanism implementation beyond verification wiring:
  **BLOCKED / UNSTARTED**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.

---

## Section 4 — Trust-Anchor & Verifier Requirement Ledger (template, to be completed later)

No verifier primitive or trust anchor exists now. A future crypto-wiring charter / implementation
must satisfy each requirement (documentation-only here; every entry is a future requirement, never
an authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| verifier_static_pin | statically pinned / allowlisted primitive | NO | BLOCKED |
| no_arbitrary_injection | no arbitrary runtime callable in prod | NO | BLOCKED |
| no_mock_in_prod | test doubles cannot cross into prod | NO | BLOCKED |
| public_key_only | no private-key / signing primitive | NO | BLOCKED |
| verifier_provenance | identity / version / fingerprint bound | NO | BLOCKED |
| day_zero_ceremony | offline fingerprint + human confirm | NO | BLOCKED |
| immutable_anchor | pinned, immutable trust-anchor artifact | NO | BLOCKED |
| independent_verify | pin verified before first use | NO | BLOCKED |
| no_self_generation | server does not mint its own anchor | NO | BLOCKED |
| no_network_anchor | anchor not network-fetched | NO | BLOCKED |
| no_model_config_anchor | not model / log / config sourced | NO | BLOCKED |
| rotation_ceremony | rotation is separate future ceremony | NO | BLOCKED |
| revocation_fail_closed | revocation fails closed, no rollover | NO | BLOCKED |

Every requirement is **unimplemented and BLOCKED**; satisfying the ratified verification slice does
not satisfy any of them, and none auto-enables S1, matrix, paper, live, or capacity.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this cryptographic wiring & trust anchor boundary charter.
2. Only under a **separate explicit operator command of the Section I shape**: a future crypto-wiring
   design that selects the production verifier primitive (none chosen here) and defines the Day-Zero
   ceremony.
3. A ratified verification slice, a trust-anchor ceremony, and passing tests do **not** auto-enable
   S1, matrix construction, paper, live, or capacity.

## Post-state

- Cryptographic Wiring & Trust Anchor Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Human Approval Package Verification slice: **RATIFIED**.
- Human Approval Ledger / Operator Decision Mechanism TDD Charter: **RATIFIED**.
- Human Approval Ledger / Operator Decision Mechanism Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Evidence Matrix Construction Boundary Charter: **RATIFIED**.
- Post-Run Read-Only Continuous Ledger Audit: **PASS / COMPLETE**.
- Frozen 24h raw ledger: **AUDITED CLEAN**.
- S1 authorization gate: **ELIGIBLE FOR SEPARATE REVIEW**.
- Human approval ledger DB: **NOT CREATED**.
- Human approval ledger / operator decision mechanism implementation beyond verification wiring:
  **BLOCKED / UNSTARTED**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
