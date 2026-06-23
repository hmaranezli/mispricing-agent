# Post-Phase 6.2 Data Retention / Redaction / Evidence Preservation Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future data retention, redaction, and
  evidence preservation. It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It **reads or mutates no** retention policy config, **creates no** redaction script, and performs
  **no** deletion, truncation, chmod / chown, compression, archive, backup, snapshot, encryption,
  upload, or export.
- It **dumps no** raw bodies, **reads or mutates no** logs, **generates no** artifact / report /
  export.
- It **does not inspect** secrets, env vars, credentials, tokens, cookies, API keys, or account
  balances.
- It performs **no** network request, **no** external service call, **no** notification (Telegram /
  API / webhook / email / SMS / pager), **no** test run.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- **Core doctrine:** retention is custody, not authority; redaction is safety transformation, not
  evidence laundering; preservation is forensic continuity, not production readiness; deletion is
  governance, not recovery; raw evidence existence is not permission to use it; privacy / security
  handling does not authorize mutation of source-of-truth evidence.
- **Monitoring / Alerting / Notification Non-Authority Boundary Charter: RATIFIED.**
- **Storage / Persistence / Artifact Export Authority Boundary Charter: RATIFIED at `1c7f4e1`'s
  parent chain.**
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Data retention / redaction / evidence preservation authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `1c7f4e12babef13ecb92013d6185443d96010bd3`.
- Parent chain:
  - `1c7f4e12babef13ecb92013d6185443d96010bd3` = **RATIFIED** Monitoring / Alerting / Notification
    Non-Authority Boundary Charter.
  - `a58596f7d7327a47bfe86dddcb084a3e33f4f2f8` = **RATIFIED** Storage / Persistence / Artifact
    Export Authority Boundary Charter.
  - `6b65c37029eaf2041e2d0fa6c9fbdc0febfd8d17` = **RATIFIED** Time / Scheduler / Clock Authority
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **data retention / redaction / evidence preservation**
  boundary. It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **custody non-authority line**: retaining, redacting, or preserving
  evidence is **custody and governance at most**, never a command, never validation, never an
  authorization, and never a license to mutate source-of-truth evidence.
- It exists to make **"redacted copy ⇒ canonical truth", "preserved raw body ⇒ S1 append", and
  "evidence laundering dirty→clean" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Data Retention / Redaction / Evidence Preservation Boundary

This charter authorizes **no** implementation, **no** deletion, **no** redaction execution, **no**
archive / export, **no** evidence mutation, **no** S1 append, **no** recovery, **no** trading, and
**no** capacity.

1. It defines **requirements only**.
2. It **deletes, redacts, archives, and mutates nothing**.
3. It **authorizes no** runtime, S1 append, trading, paper / canary / live, recovery, routing, or
   capacity.

### Gate B — Preconditions Chain

Before any future retention / redaction / preservation action may be **eligible**, all of the
following must hold:

1. an **explicit operator command** names the scope (per the Operator Authorization boundary);
2. an **immutable source reference** identifies the exact evidence;
3. a **digest / manifest** covers the evidence;
4. **provenance binding** is present (source authority + commit SHA + source event reference);
5. a **retention purpose** is explicitly stated;
6. **redaction rule provenance** is present (which rule, which version, immutable identity);
7. **raw / source-of-truth separation** is preserved (the original is never replaced);
8. a **privacy / security classification** is assigned;
9. **no implicit latest-file selection** — evidence is referenced explicitly;
10. **no model / agent bridge** and **no config / flag bridge** promote a retention/redaction action
    to authority;
11. **no S1 / capacity implication** — no retention/redaction action implies S1 append or any
    capacity change.

Any unmet precondition ⇒ the action is **not eligible** and **fails closed**.

### Gate C — Data / Evidence Class Taxonomy (fail-closed default)

Future classification must define a closed taxonomy covering at least:

- **raw HTTP body**;
- **normalized raw ledger row**;
- **S1 row**;
- **stdout / stderr log**;
- **tmux transcript**;
- **audit report**;
- **generated docs artifact**;
- **manifest / checksum**;
- **cache**;
- **backup / snapshot**;
- **redacted copy**;
- **quarantine artifact**;
- **secret-bearing text**;
- **operator note**;
- **external upload / sync target**.

Each data / evidence item must map to exactly one class; **any unclassified class fails closed**.

### Gate D — Retention-Is-Not-Authority Doctrine

Future systems must prove:

- **retained evidence ≠ audit clean.**
- **preserved raw body ≠ source promotion.**
- **redacted copy ≠ canonical truth.**
- **deletion request ≠ recovery permission.**
- **backup exists ≠ rollback permission.**
- **manifest exists ≠ S1 append.**
- **quarantine exists ≠ defect fixed.**
- **operator note ≠ operator command.**
- **secret removed from view ≠ secret absence.**
- **evidence age ≠ capacity.**

### Gate E — Redaction and Provenance Rules

Future redaction / retention records must:

- carry an **explicit original artifact reference**;
- carry an **immutable digest before / after** where applicable;
- carry a **redaction rule identity**;
- carry a **redaction reason**;
- carry a **redactor identity / class**;
- treat **UTC timestamp as forensic metadata only** (never authority, never source event time);
- **never use SQLite `rowid` / `append_sequence` as a domain identity** (identity derives from
  content / provenance hashes only);
- use **no implicit "latest-artifact" selection** — artifacts are referenced explicitly;
- be **quarantined on missing provenance**;
- **strictly never mutate original source artifacts to make them appear clean** (no evidence
  laundering — the original source-of-truth is immutable; redaction produces a *separate* derived
  copy).

### Gate F — Evidence Preservation / Privacy / Secret Firewall

1. Retention or redaction may **not** trigger audit-clean status, report-clean status, S1 append,
   recovery, restart, rollback, paper / canary / live promotion, calibration, trade candidate
   generation, model input for action, alerting escalation, or capacity changes.
2. **Secret / privacy handling must never become authority** to inspect secrets, credentials,
   wallets, env vars, or private keys — handling secret-bearing text means **isolating and not
   reading** it, never inspecting it.
3. Preservation is **forensic continuity, not production readiness**.

### Gate G — Retention / Redaction / Preservation Failure Doctrine

Future systems must **fail closed** for:

- missing original digest;
- digest mismatch;
- missing redaction rule;
- ambiguous redaction scope;
- partial redaction;
- irreversible source mutation;
- mixed-run artifact;
- stale retention class;
- unknown privacy class;
- secret-bearing ambiguity;
- duplicate artifact identity;
- backup / source disagreement;
- manifest / report disagreement;
- external upload ambiguity.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Explicitly Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `redacted copy ⇒ canonical evidence`
- `preserved raw body ⇒ S1 append`
- `clean-looking artifact ⇒ audit clean`
- `backup ⇒ rollback`
- `deletion ⇒ recovery`
- `quarantine ⇒ defect fixed`
- `retention age ⇒ capacity`
- `operator note ⇒ operator command`
- `secret redaction ⇒ credential authority`
- `external upload ⇒ third-party authority`
- `latest retained file ⇒ implicit input`
- `model summary of redacted evidence ⇒ actionability`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Documentation-Only Output Boundary

1. This file is a **charter only**.
2. It must **not create, inspect, mutate, delete, redact, archive, export, upload, validate, or
   summarize** any runtime / log / ledger / artifact evidence.
3. **No** deletion, truncation, chmod / chown, compression, archive, backup, snapshot, encryption,
   upload, or export.
4. **No** S1 append, **no** production stream, **no** signal / trade / order / routing / capital
   output.
5. **Capacity remains 0.**

### Gate J — No-Auto-Activation Next Gate

1. After ratification, the next **docs-only** gate **may** be a **Post-Run Audit Report Artifact
   Boundary Charter** — but **no runtime / actionable gate changes**.
2. The **runtime / actionable gate remains unchanged**: wait for the bounded raw-only 24h run
   completion / stop, then a **separately authorized Read-Only Continuous Ledger Audit**.
3. **Clean audit still does not auto-enable S1 or capacity.**
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.** **Capacity remains 0.**

---

## Section 4 — Evidence Class Custody Ledger (template, to be completed later)

No evidence action is asserted as authority now. A future retention/redaction charter /
implementation must map each class into this structure (documentation-only here; **never** record a
secret value):

| Class | Custody role | Source mutable? | Provenance-bound | Status |
|-------|--------------|-----------------|------------------|--------|
| raw_http_body | source-of-truth | NO (immutable) | yes (active run) | preserved, read-only audit pending |
| normalized_raw_ledger_row | source-of-truth | NO (append-only) | yes | preserved |
| s1_row | derived | NO | PENDING | BLOCKED |
| stdout_stderr_log | observation | NO | PENDING | non-authoritative |
| tmux_transcript | observation | NO | PENDING | non-authoritative |
| audit_report | observation | NO | PENDING | BLOCKED (audit unstarted) |
| generated_docs_artifact | artifact | NO | PENDING | non-authoritative |
| manifest_checksum | integrity | NO | PENDING | non-authoritative |
| cache | derived | NO | PENDING | non-authoritative |
| backup_snapshot | custody | NO | PENDING | BLOCKED |
| redacted_copy | derived (separate) | NO (never replaces source) | PENDING | BLOCKED |
| quarantine_artifact | custody | NO | PENDING | BLOCKED |
| secret_bearing_text | isolate-not-read | NO | PENDING | BLOCKED |
| operator_note | observation | NO | PENDING | non-authoritative |
| external_upload_sync | target | NO | PENDING | BLOCKED |

Every class is **non-authoritative**; original source-of-truth evidence is immutable and is never
mutated to appear clean.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this data retention / redaction / evidence preservation boundary charter.
2. Next **docs-only** gate may be a Post-Run Audit Report Artifact Boundary Charter.
3. Runtime / actionable gate remains unchanged: bounded raw-only 24h run completion / stop →
   separately authorized Read-Only Continuous Ledger Audit. Clean audit does not auto-enable S1 or
   capacity.

## Post-state

- Data Retention / Redaction / Evidence Preservation Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- Monitoring / Alerting / Notification Non-Authority Boundary Charter: **RATIFIED**.
- Storage / Persistence / Artifact Export Authority Boundary Charter: **RATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Secrets / credentials / wallet / signing / capital authority: **BLOCKED**.
- External dependency / third-party service authority: **BLOCKED**.
- Model / agent authority: **BLOCKED**.
- Configuration / parameter / feature-flag authority: **BLOCKED**.
- Time / scheduler / clock authority: **BLOCKED**.
- Storage / persistence / artifact export authority: **BLOCKED**.
- Monitoring / alerting / notification authority: **BLOCKED**.
- Data retention / redaction / evidence preservation authority: **BLOCKED**.
- Capacity: **0**.
