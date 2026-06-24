# Post-Phase 6.2 Ingress, Authentication & CLI/API Trigger Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines when — and **only** when — a future external **trigger
  surface** (CLI / API / network / authenticated ingress) could someday *request* execution of the
  ratified Production S1 Append Execution Wiring/Circuit library. It **implements no ingress / auth /
  CLI / API / network / socket / server**, **connects no trigger to the circuit**, **adds no
  dependency**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** live S1 DB creation / modification, **no** S1 append, **no**
  production stream, **no** writer / circuit / initializer execution, **no** approval-ledger mutation,
  **no** signing / verification implementation.
- It inspects **no** private key / wallet / credential / secret / env, implements **no** GPG /
  YubiKey / HSM / Tails / offline-salt; reads **no** raw ledger / body / payload.
- It performs **no** network / API / monitoring / tmux / runtime interaction, **no** paper /
  dry-run / live / canary, **no** trading / capacity inference, **no** report / export / artifact
  generation.
- **Core doctrine:** **external ingress is not execution and not authorization.** An ingress pass, an
  auth pass, a CLI/API parse success, or a valid request shape is **never** S1 append authorization.
  Ingress may at most produce a **passive, frozen, digest-bound command candidate** for separate later
  review.
- **PRODUCTION ACTIVATION BLOCKER:** **Schema/Journal Unification is UNSTARTED.** The ratified
  initializer provisions `s1_appends` in **WAL** mode; the ratified writer appends to its **own**
  `s1_append_log` table with rollback-journal behavior. The current circuit is **lab/test valid
  only** and **must not** be used for production append activation until this mismatch is resolved by
  a separate ratified boundary + runtime/TDD refactor.
- **Production S1 Append Execution Wiring/Circuit runtime slice: RATIFIED.**
- **Live S1 DB production path: NOT CREATED.** **S1 append: DENIED.** **Production S1 stream:
  BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `7a9260c6204ced07aa1648a160625d0dc7f0bb1c`.
- Parent chain:
  - `7a9260c6204ced07aa1648a160625d0dc7f0bb1c` = **RATIFIED** Production S1 Append Execution
    Wiring/Circuit runtime slice (`approval/production_s1_append_circuit.py`; library-only, test-path
    only; success = `APPEND_RECORDED_IN_TEST_CONTAINER`; all production authority flags `False`).
  - `1514ca847c98127a9448e05d045f7a666c28ccba` = **RATIFIED** Production S1 Append Execution
    Wiring/Circuit Boundary Charter.
  - `cd9027a0b4ef4fa5e4a368790a436a0a56a89f1d` = **RATIFIED** Live S1 DB Initialization & Schema
    Provisioning runtime slice.
  - `d15f908396143768f1024a38385d2845cd7bff66` = **RATIFIED** S1 DB Recovery Protocol Boundary
    Charter.
- This charter defines the **Ingress, Authentication & CLI/API Trigger** boundary. It does **not**
  supersede, relax, or accelerate any prior gate. It sits **upstream** of any external request and
  **connects nothing**.

## Section 2 — Charter Intent

- The circuit is the most downstream ratified library: it can, in a TEST container, compose the
  decision/initializer/writer into one explicitly-commanded append. But it is invoked **only** by a
  trusted in-process caller passing a frozen command; **no external surface exists** to trigger it.
- This charter draws the line for any future **external trigger**: even a perfectly authenticated,
  well-formed, signature-valid CLI/API request **does not authorize an S1 append**. It may at most be
  transformed into a **passive command candidate** that a separate, explicitly-commanded review may
  later consider — and **not even that** until the Schema/Journal Unification production blocker is
  resolved.
- It exists to make **"request authenticated ⇒ run circuit"**, **"CLI parsed ⇒ append"**, and
  **"ingress reachable ⇒ production live"** drift **structurally impossible**, and to pin the
  air-gapped-style auth, replay-protection, and no-default-route requirements as hard boundaries on a
  surface that is **not** being built here.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only / No Authority / No Auto-Activation

1. This charter authorizes **no** runtime behavior and **builds no ingress / auth / CLI / API**.
2. It opens **no** socket / server / port / route, parses **no** request, verifies **no** signature.
3. It does **not** execute the circuit, initializer, or writer; performs **no** append; starts **no**
   stream.
4. It does **not** create trading, paper, canary, live, wallet, signing, capital, or capacity
   authority.
5. **No auto-activation.** Any future ingress must be **separately and explicitly user-authorized**
   and must never be wired to the circuit by import, request arrival, auth success, scheduler, hook,
   callback, queue, worker, observer, listener, webhook, or bot.

### Gate B — Ingress Is Not Execution / Not Authorization

1. **External ingress is not execution and not authorization.**
2. An **ingress pass**, an **auth pass**, a **CLI/API parse success**, and a **valid request shape**
   are each **evidence at most**, never S1 append authorization.
3. A request that survives every future ingress check is, at most, a **passive command candidate** for
   separate review.

### Gate C — Separation of Ingress/Auth from Circuit Orchestration

1. Authentication and ingress must be **architecturally separate** from circuit orchestration.
2. Ingress may **only** produce a **passive, frozen, digest-bound command candidate**; it must **not**
   call the circuit, initializer, or writer.
3. The hand-off from a verified candidate to any execution review is a **separate, explicitly
   commanded** step — never an in-line call from the ingress handler.
4. The ingress layer holds **no** authority object and emits **no** authority flag.

### Gate D — Required Future Trigger Command Object Fields

A future external trigger command candidate must carry **all** of these explicit fields (passive,
frozen):

- `operator_command_id`;
- `operator_identity_reference`;
- `command_scope`;
- `target_circuit_digest`;
- `decision_result_digest`;
- `initializer_result_digest`;
- `writer_expectation_digest`;
- `db_path_digest` (a digest binding the path — **not** a raw mutable path alone);
- `s1_target`;
- `evidence_digest`;
- `canonical_payload_digest`;
- `approval_row_digest`;
- `freshness_binding_digest`;
- `immutable_snapshot_ref`;
- `request_timestamp_reference`;
- `replay_protection_nonce_or_sequence`;
- `command_digest`.

Any missing, empty, or ambiguous field **fails closed**. The presence of all fields is **necessary,
never sufficient**.

### Gate E — Cryptographic Authentication Boundary

1. **Public-key-only verifier on the VPS.** The VPS holds **no private key**.
2. The operator key / fingerprint must be **explicitly allowlisted** (pinned), not discovered.
3. Authentication requires a **detached signature over the canonical command bytes**; the shown bytes
   must equal the signed bytes (anti-blind-signing).
4. Signing happens **off-VPS / air-gapped**; the VPS only **verifies**.
5. A verification pass is **authentication evidence**, never S1 append authority (Gate B).

### Gate F — Replay Protection

1. **Nonce / sequence uniqueness** must be enforced and durably recorded.
2. **`command_digest` uniqueness** must be enforced (a replayed digest fails closed).
3. **Expiry / freshness** must bind to explicit `request_timestamp_reference` /
   `immutable_snapshot_ref` evidence — **no wall-clock-only trust**, no implicit TTL.
4. A reused nonce, reused sequence, reused command_digest, or stale request **fails closed**.

### Gate G — CLI / API / Network Trigger Boundaries

1. **No default route** and no implicit endpoint.
2. **No unauthenticated local CLI shortcut.**
3. **No environment-variable authority** (env never grants execution).
4. **No bearer-token-only authority** (a bearer token alone is insufficient).
5. **No socket listener / server / port** until separately ratified.
6. Every future surface is **deny-by-default**; absence of an explicit, ratified, authenticated path
   means **no trigger**.

### Gate H — No Dependency / Framework Authorization

1. This charter authorizes **no** dependency or framework addition.
2. **No** `argparse` / `click` / `typer` / `flask` / `fastapi` / `http` / server / `socket` /
   `webhook` / `telegram` / `bot` integration is introduced or approved here.
3. Any future framework adoption requires a **separate, explicit ratification** with its own
   dependency-and-supply-chain review.

### Gate I — Production Activation Blocker (Schema/Journal Unification)

1. **Schema/Journal Unification is UNSTARTED and is a PRODUCTION BLOCKER.**
2. The ratified **initializer** provisions table **`s1_appends`** in **WAL** mode; the ratified
   **writer** appends to its **own** table **`s1_append_log`** with rollback-journal behavior. The
   current circuit verifies the `s1_appends` container and delegates the append to the writer's
   `s1_append_log` — which is **lab/test valid only**.
3. **No ingress / auth / CLI / API trigger may connect to a live circuit** until the
   initializer/writer **schema + journal mismatch** is resolved by a **separate ratified boundary**
   and a **runtime/TDD refactor**.
4. The current circuit **must not** be used for production append activation in its present form.

### Gate J — Pre-Authorization Fail-Closed Chain

Any external trigger attempt **fails closed** if it occurs before each of these separate, explicit
authorizations exists:

1. **before Schema/Journal Unification** is resolved and ratified;
2. **before live DB creation / provisioning authorization**;
3. **before production append authorization**;
4. **before production stream authorization**.

Each is an independent gate; satisfying one does not imply any other.

### Gate K — Ingress/Auth Non-Action Rules

Ingress / auth must **not**:

1. initialize a DB;
2. call the writer;
3. call the circuit;
4. append rows;
5. mutate the approval ledger;
6. start a production stream;
7. start a scheduler / queue / worker / observer / listener;
8. infer trade / order / capacity / actionability;
9. read secrets / wallets / private keys / env vars;
10. hold or emit any authority flag.

### Gate L — Fail-Closed Conditions (at least forty-five)

The following must **fail closed** (default = **no candidate accepted, no trigger, no execution**):

1. Schema/Journal Unification unresolved;
2. live DB creation not separately authorized;
3. production append not separately authorized;
4. production stream not separately authorized;
5. missing `operator_command_id`;
6. missing `operator_identity_reference`;
7. missing `command_scope`;
8. missing `target_circuit_digest`;
9. `target_circuit_digest` mismatch;
10. missing `decision_result_digest`;
11. missing `initializer_result_digest`;
12. missing `writer_expectation_digest`;
13. missing `db_path_digest`;
14. raw mutable path supplied instead of `db_path_digest`;
15. `db_path_digest` mismatch;
16. missing `s1_target`;
17. `s1_target` mismatch;
18. missing `evidence_digest`;
19. missing `canonical_payload_digest`;
20. missing `approval_row_digest`;
21. missing `freshness_binding_digest`;
22. freshness binding mismatch;
23. missing `immutable_snapshot_ref`;
24. missing `request_timestamp_reference`;
25. missing `replay_protection_nonce_or_sequence`;
26. missing `command_digest`;
27. `command_digest` mismatch (recompute differs);
28. reused nonce / sequence;
29. reused `command_digest` (replay);
30. expired / stale request;
31. wall-clock-only freshness (no explicit binding);
32. private key present on VPS;
33. operator key / fingerprint not allowlisted;
34. signature missing;
35. signature invalid;
36. shown bytes ≠ signed bytes (blind-signing);
37. default route / implicit endpoint used;
38. unauthenticated local CLI shortcut;
39. environment-variable authority asserted;
40. bearer-token-only authority asserted;
41. socket listener / server / port opened without ratification;
42. framework/dependency introduced without ratification;
43. ingress calling circuit / initializer / writer directly;
44. ingress appending rows / mutating ledger;
45. ingress starting stream / scheduler / queue / worker / observer;
46. ingress inferring trade / order / capacity;
47. ingress reading secret / wallet / key / env;
48. any execution token created at ingress.

The default in **every** degraded, ambiguous, or unverified state is the **safe / no-trigger /
blocked** outcome.

### Gate M — Required Future Ingress/Auth/Trigger Command Shape (ingress only)

Any future ingress / auth / trigger implementation command must:

- be **separately and explicitly authorized by the user** (Gemini verdict ≠ command; Claude output ≠
  command);
- start from an **exact SHA**;
- be **RED first** (watch the missing ingress seam fail before any code);
- be scoped to **ingress / auth / command-candidate construction only** — **no** circuit execution,
  **no** DB init, **no** append, **no** stream, **no** trading/capacity;
- be gated behind the resolved **Schema/Journal Unification** ratification (Gate I);
- include **targeted tests** for: all required command fields, public-key-only verification, pinned
  allowlist, detached-signature-over-canonical-bytes, anti-blind-signing, nonce/sequence/command_digest
  replay protection, explicit-freshness (no wall-clock-only), no-default-route, no-env-authority,
  no-bearer-only-authority, no-socket-until-ratified, candidate-is-passive (no circuit/DB/append
  side-effect), and no-authority output;
- introduce **no** dependency/framework without a separate ratified supply-chain review;
- **run the full approval suite**;
- **preserve S1 append DENIED**, production stream BLOCKED, capacity 0, and Live S1 DB production path
  NOT CREATED;
- create **no** trading / order / capacity / wallet / paper / live / canary authority.

This section grants **no** current authority; absent such a command, **no ingress, auth, CLI, or API
trigger is built, connected, or executed.**

---

## Section 4 — Ingress/Auth Requirement Ledger (template, to be completed later)

No ingress / auth / trigger mechanism exists now. A future ingress charter / implementation must
satisfy each requirement (documentation-only here; every entry is a future requirement, never an
authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| ingress_not_execution | ingress/auth/parse pass never authorizes append | NO | BLOCKED |
| passive_candidate_only | ingress yields a frozen digest-bound candidate only | NO | BLOCKED |
| separation_of_concerns | ingress/auth separate from circuit orchestration | NO | BLOCKED |
| full_command_fields | all required trigger command fields present | NO | BLOCKED |
| public_key_only | VPS verifier holds no private key | NO | BLOCKED |
| pinned_allowlist | operator key/fingerprint explicitly allowlisted | NO | BLOCKED |
| detached_signature | detached sig over canonical command bytes | NO | BLOCKED |
| anti_blind_signing | shown bytes == signed bytes | NO | BLOCKED |
| replay_protection | nonce/sequence/command_digest uniqueness | NO | BLOCKED |
| explicit_freshness | freshness bound to explicit refs, no wall-clock-only | NO | BLOCKED |
| no_default_route | no default route / implicit endpoint | NO | BLOCKED |
| no_env_authority | env vars never grant execution | NO | BLOCKED |
| no_bearer_only | bearer token alone insufficient | NO | BLOCKED |
| no_socket_until_ratified | no listener/server/port until ratified | NO | BLOCKED |
| no_framework_without_ratification | no argparse/click/flask/fastapi/socket/bot | NO | BLOCKED |
| schema_journal_unified | initializer/writer schema+journal unified first | NO | BLOCKED |
| no_side_effects | ingress never calls circuit/DB/append/ledger/stream | NO | BLOCKED |
| no_authority_output | all authority flags false | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable a DB
creation, S1 append, production stream, paper, live, trading, or capacity.

## Section 5 — Non-Authority Rules

Future systems must prove:

- **external ingress ≠ execution.**
- **ingress pass ≠ authority.**
- **auth pass ≠ authority.**
- **CLI/API parse success ≠ authority.**
- **valid request shape ≠ authority.**
- **valid command candidate ≠ S1 append authority.**
- **signature valid ≠ S1 append authority.**
- **`REVIEWABLE_FOR_S1_APPEND` ≠ AUTHORIZED.**
- **`CREATED_EMPTY_LOCKED_CONTAINER` ≠ AUTHORIZED.**
- **`APPEND_RECORDED_IN_TEST_CONTAINER` ≠ `PRODUCTION_APPEND_AUTHORIZED`.**
- **docs charter ≠ authority.**
- **Gemini verdict ≠ operator command.**
- **Claude output ≠ operator command.**
- **no S1 append. no production stream. no DB creation/modification. no trade / order / execute.
  no paper / canary / live. no wallet / signing / capital. no capacity. no execution token.**

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this Ingress, Authentication & CLI/API Trigger Boundary Charter.
2. A separate **Schema/Journal Unification** boundary + runtime/TDD refactor (PRODUCTION BLOCKER)
   resolving the initializer (`s1_appends`, WAL) vs writer (`s1_append_log`, rollback-journal)
   mismatch before any production activation.
3. Only under a **separate, explicitly user-authorized command of the Section M shape**, and only
   after the blocker is resolved: a future ingress / auth / trigger slice (RED-first, fail-closed,
   public-key-only, replay-protected, no-default-route, candidate-only, no trading/capacity authority).
4. No artifact — circuit, decision, initializer container, writer, valid command candidate, signature,
   or auth pass — auto-enables a DB creation, S1 append, production stream, paper, live, trading, or
   capacity.

## Post-state

- Ingress, Authentication & CLI/API Trigger Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Production S1 Append Execution Wiring/Circuit runtime slice: **RATIFIED**.
- Production S1 Append Execution Wiring/Circuit Boundary Charter: **RATIFIED**.
- Live S1 DB Initialization & Schema Provisioning runtime slice: **RATIFIED**.
- S1 DB Recovery Protocol Boundary Charter: **RATIFIED**.
- Schema/Journal Unification: **UNSTARTED / PRODUCTION BLOCKER**.
- Live S1 DB production path: **NOT CREATED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
