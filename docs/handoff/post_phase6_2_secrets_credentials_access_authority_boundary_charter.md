# Post-Phase 6.2 Secrets / Credentials / Access Authority Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future secrets, credentials,
  wallet / API-key authority, access control, and credential provenance. It **does not inspect or
  create secrets**. It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It **does not read, print, dump, validate, or infer** any secret; it does **not** inspect
  environment variables, API keys, private keys, wallet keys, credentials, tokens, cookies, or
  account balances.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, paper / canary / live, routing, orders, fills, cancels, sizing, allocation,
  capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Halt / Restart / Rollback / Recovery Boundary Charter: RATIFIED at `89fed1f`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Halt / restart / rollback / recovery: BLOCKED.**
- **Secrets / credentials / wallet / signing / capital authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `89fed1fdb88676b7d7bd5533e4c7571ce7ef5526`.
- Parent chain:
  - `89fed1fdb88676b7d7bd5533e4c7571ce7ef5526` = **RATIFIED** Halt / Restart / Rollback / Recovery
    Boundary Charter.
  - `392cb8cc1fdb943aa671040daeeaf376c230b6a4` = **RATIFIED** Failure Surface / Incident Response
    Boundary Charter.
  - `1a35aeafc256811c4849b5b6b46a51508f65461d` = **RATIFIED** Operator Authorization / Human
    Command Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **secrets / credentials / access authority** boundary. It
  does not supersede, relax, or accelerate any prior gate.

## Section 2 — Constitutional Anchoring (binding floors)

The existing constitution (`CLAUDE.md`) governs evidence and live transitions; this charter extends
that discipline to credential material:

- No price / funding / probability / movement may be written from memory or estimate — by the same
  rule, **no secret value may ever be written, logged, or inferred** into any artifact.
- Live (`DRY_RUN=False`) only by explicit human written command; capital authority therefore
  remains human-gated.
- `config.py` guardrail constants are immutable without human action.

## Section 3 — Boundary Gates

### Gate A — Future-Only Secrets / Access Boundary

1. This charter defines **requirements only**.
2. It **does not inspect** secrets.
3. It **does not create** credentials.
4. It **does not authorize** runtime, S1 append, trading, paper / canary / live, routing, or
   capacity.

### Gate B — Preconditions Before Any Future Credential / Access Work

Future credential / access work requires:

1. Operator Authorization / Human Command Boundary Charter **ratified**;
2. Paper / Canary / Live firewall **ratified**;
3. Halt / Restart / Rollback / Recovery boundary **ratified**;
4. an **exact future operator command**;
5. the **exact target subsystem**;
6. the **exact allowed credential class**;
7. the **exact forbidden actions**;
8. the **explicit S1 append state**;
9. the **explicit capacity state**;
10. the **explicit paper / canary / live state**;
11. **DIRTY state blocks implementation** unless the task is **documentation-only**.

### Gate C — Credential Class Taxonomy

Future classification must define a closed taxonomy covering at least:

- **public non-secret configuration**;
- **exchange / API credentials**;
- **wallet / private-key material**;
- **account / balance authority**;
- **signing authority**;
- **webhook / token / cookie / session material**;
- **cloud / server access credentials**;
- **notification credentials**;
- **read-only credentials**;
- **write / trade-capable credentials**;
- **emergency / operator credentials**.

Each credential must map to exactly one class; an unclassifiable credential is treated as the most
restrictive class and **fails closed**.

### Gate D — Secret Non-Exposure Doctrine

Future systems must prove **no secret values** appear in any of:

- logs;
- docs;
- test fixtures;
- commits;
- reports;
- screenshots;
- exceptions;
- telemetry;
- model prompts or agent transcripts.

Secret material may only ever be referenced by **non-secret identifiers** (class + scope +
provenance handle), never by value.

### Gate E — Authority Separation

1. **Read-only credentials must not imply write credentials.**
2. **Write credentials must not imply trade credentials.**
3. **Trade credentials must not imply withdrawal credentials.**
4. **Paper credentials must not imply canary / live credentials.**
5. **Canary credentials must not imply live credentials.**
6. **Account balance visibility must not imply capital deployment authority.**
7. **API reachability must not imply authorization.**

Each escalation across these lines requires a separate explicit operator command satisfying the
Operator Authorization boundary.

### Gate F — Wallet / Signing / Capital Firewall

1. **Wallet keys and signing authority require a separate future charter.**
2. **Withdrawal authority is out of scope and BLOCKED.**
3. **Capital deployment authority is out of scope and BLOCKED.**
4. Any **signing operation requires a separate future operator command**.
5. Any **missing / ambiguous wallet authority fails closed**.
6. **No agent / model / scheduler / background process may self-authorize signing.**

### Gate G — Provenance and Access Audit Requirements

Future access records must be:

- **operator-command-bound**;
- **commit / base-SHA-bound**;
- **credential-class-bound**;
- **scope-bound**;
- **timestamped**;
- **non-secret-value-preserving** (records carry class / scope / provenance handles only — never
  secret values);
- **deterministic and reproducible**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only);
- **stored only in a separately authorized mechanism** (this charter creates no such store).

### Gate H — Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `config presence ⇒ credential authority`
- `API key presence ⇒ trading authority`
- `wallet key presence ⇒ signing authority`
- `account balance visibility ⇒ capacity`
- `successful authentication ⇒ S1 append`
- `successful authentication ⇒ trading`
- `paper credential ⇒ canary / live credential`
- `canary credential ⇒ live credential`
- `model inference ⇒ credential use`
- `scheduler event ⇒ credential use`
- `incident recovery ⇒ credential activation`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** secret inspection.
3. **No** credential creation.
4. **No** environment dump.
5. **No** access-token creation.
6. **No** wallet / signing action.
7. **No** S1 append.
8. **No** production stream.
9. **No** signal / trade / order / routing / capital output.
10. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future credential-access **TDD** requires a separate explicit operator command.
2. Future credential-access **implementation** requires a separate explicit operator command.
3. Future **wallet / signing / capital authority** requires a separate explicit charter and command.
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.**
6. **Capacity remains 0.**

---

## Section 4 — Credential Class Authority Ledger (template, to be completed later)

No credential is asserted now. A future credential-access charter / implementation must map each
class into this structure (documentation-only here; **never** record a secret value):

| Credential class | Authority level | Implies (none unless chartered) | Operator-gated | Status |
|------------------|-----------------|---------------------------------|----------------|--------|
| public_non_secret_config | read-only | nothing | n/a | PENDING |
| exchange_api | PENDING | nothing | PENDING | PENDING |
| wallet_private_key | PENDING | nothing | PENDING | BLOCKED |
| account_balance_authority | PENDING | nothing | PENDING | PENDING |
| signing_authority | PENDING | nothing | PENDING | BLOCKED |
| webhook_token_cookie_session | PENDING | nothing | PENDING | PENDING |
| cloud_server_access | PENDING | nothing | PENDING | PENDING |
| notification | PENDING | nothing | PENDING | PENDING |
| read_only | read-only | nothing | PENDING | PENDING |
| write_trade_capable | PENDING | nothing | PENDING | BLOCKED |
| emergency_operator | PENDING | nothing | PENDING | PENDING |

All rows carry **no secret values**; wallet / signing / trade-capable remain BLOCKED until separately
chartered.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this secrets / credentials / access authority boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command: a separate credential-access TDD charter, then a
   RED→GREEN implementation.
4. Wallet / signing / capital authority remains behind its **own** separate charter and operator
   command, and the constitutional human-command floor for live / capital.

## Post-state

- Secrets / Credentials / Access Authority Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Secrets / credentials / wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
