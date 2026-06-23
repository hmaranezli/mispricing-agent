# Post-Phase 6.2 Storage / Persistence / Artifact Export Authority Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements proving that **persistence is evidence,
  not authority; export is artifact, not action; report is observation, not permission**.
- It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It **creates no** storage, sqlite / WAL, cache, or backup; it **mutates no** log; it **generates
  no** artifact / export / report.
- It **does not inspect** secrets, env vars, credentials, tokens, cookies, API keys, or account
  balances.
- It performs **no** network request, **no** external service call, **no** test run.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- **Core doctrine:** persistence is evidence, not authority; export is artifact, not action; report
  is observation, not permission; file existence is not operator command; audit-clean is not S1
  authorization; artifact generation is not capacity activation.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Time / Scheduler / Clock Authority Boundary Charter: RATIFIED at `6b65c37`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Storage / persistence / artifact export authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `6b65c37029eaf2041e2d0fa6c9fbdc0febfd8d17`.
- Parent chain:
  - `6b65c37029eaf2041e2d0fa6c9fbdc0febfd8d17` = **RATIFIED** Time / Scheduler / Clock Authority
    Boundary Charter.
  - `55e25ae9468f318805e475add6e542c14ab01b10` = **RATIFIED** Configuration / Parameter /
    Feature-Flag Authority Boundary Charter.
  - `ff0fa0f5306f1dd3acec9a6e7239dd1dc0a36651` = **RATIFIED** Model / Agent Output Non-Authority
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **storage / persistence / artifact export authority**
  boundary. It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **persistence non-authority line**: a stored file, a row count, a generated
  report, a checksum match, or an export is **evidence or artifact at most**, never a command, never
  a validation result, never an authorization.
- It exists to make **"file exists ⇒ permission", "clean report ⇒ S1 append", and "artifact
  generated ⇒ capacity" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Storage / Persistence / Artifact-Export Authority Boundary

This charter authorizes **no** implementation, **no** audit execution, **no** S1 append, **no**
export creation, **no** report generation, **no** recovery, **no** trading, and **no** capacity.

1. It defines **requirements only**.
2. It **creates no** storage and **generates no** artifact.
3. It **authorizes no** runtime, S1 append, trading, paper / canary / live, recovery, routing, or
   capacity.

### Gate B — Preconditions Chain

Before any future artifact / export / report / storage output may be treated as **eligible
evidence**, all of the following must hold:

1. the bounded raw-only 24h run is **complete / stopped**;
2. a **separate read-only audit authorization** exists (run completion alone does not authorize it);
3. **provenance binding** is present (source authority + commit SHA + input refs);
4. an **immutable digest / manifest** covers the artifact;
5. an **explicit human operator command** names the scope (per the Operator Authorization boundary);
6. **S1 stream authorization is separated** — no artifact implies S1 append;
7. **no capacity implication** — no artifact changes capacity (stays 0);
8. **no report-to-action bridge** — no report becomes a signal / trade / order;
9. **no scheduler bridge** — no timer / cron / tick promotes an artifact to authority;
10. **no model / agent bridge** — no model output promotes an artifact to authority;
11. **no config / flag bridge** — no config value or feature flag promotes an artifact to authority.

Any unmet precondition ⇒ the artifact is **not eligible evidence** and **fails closed**.

### Gate C — Storage / Persistence / Artifact Taxonomy (fail-closed default)

Future classification must define a closed taxonomy covering at least:

- **raw ledger**;
- **S1 ledger**;
- **sqlite / WAL file**;
- **append log**;
- **audit report**;
- **JSON export**;
- **CSV export**;
- **manifest / checksum**;
- **cache**;
- **backup / snapshot**;
- **stdout / stderr / log text**;
- **generated markdown / doc artifact**;
- **external upload / sync target**.

Each persistence / export item must map to exactly one class; **any unclassified persistence /
export class fails closed**.

### Gate D — Persistence-Is-Not-Authority Doctrine

Future systems must prove:

- **file exists ≠ permission.**
- **row count ≠ clean audit.**
- **clean report ≠ S1 append.**
- **S1 file exists ≠ production stream.**
- **CSV / JSON exists ≠ signal.**
- **cache hit ≠ truth.**
- **checksum match ≠ trade permission.**
- **backup exists ≠ recovery permission.**
- **report summary ≠ operator command.**
- **artifact path ≠ capacity.**

### Gate E — Artifact Provenance and Identity Rules

Future artifacts must:

- carry **explicit source provenance**;
- reference **immutable input refs**;
- carry a **digest / manifest**;
- treat **UTC retrieval timestamp as forensic metadata only** (never source event time, never
  authority);
- **never use SQLite `rowid` / `append_sequence` as a domain identity** (identity derives from
  content / provenance hashes only);
- use **no implicit "latest-file" selection** — inputs are named explicitly;
- be **quarantined on missing provenance**;
- **never mutate source artifacts to make them "clean"** (no laundering of dirty evidence).

### Gate F — Export / Report / Analytics Firewall

1. Exports and reports may **not** produce ranking, advice, threshold actionability, trade
   candidates, sizing, allocation, routing, paper / canary / live promotion, alert-triggered
   recovery, S1 append, or capacity changes.
2. Any future report must remain **offline evidence-only** unless a later explicit gate says
   otherwise.
3. A report is **observation, not permission**; an export is **artifact, not action**.

### Gate G — Storage Failure / Degradation Doctrine

Future systems must **fail closed** for:

- partial write;
- missing manifest;
- digest mismatch;
- duplicate artifact id;
- unknown schema;
- unexpected file permission;
- stale artifact;
- mixed-run artifact;
- missing source ref;
- clock / provenance ambiguity;
- cache / report disagreement;
- export target ambiguity.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Explicitly Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `raw ledger ⇒ S1 append`
- `clean report ⇒ production stream`
- `CSV export ⇒ signal`
- `JSON export ⇒ model input for action`
- `file count ⇒ capacity`
- `report artifact ⇒ paper / canary / live`
- `backup ⇒ rollback / recovery`
- `cache ⇒ source of truth`
- `latest file ⇒ implicit input`
- `rowid ⇒ domain identity`
- `external upload ⇒ third-party authority`
- `generated doc ⇒ operator command`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Documentation-Only Output Boundary

1. This file is a **charter only**.
2. It must **not create, inspect, mutate, export, validate, or summarize** runtime artifacts.
3. **No** storage creation, **no** sqlite / WAL creation, **no** cache creation, **no** log
   mutation, **no** export / report generation.
4. **No** S1 append, **no** production stream, **no** signal / trade / order / routing / capital
   output.
5. **Capacity remains 0.**

### Gate J — No-Auto-Activation Next Gate

1. After ratification, the next **docs-only** gate **may** be a **Monitoring / Alerting /
   Notification Non-Authority Boundary Charter** — but **no runtime / actionable gate changes**.
2. The **runtime / actionable gate remains**: wait for the bounded raw-only 24h run completion /
   stop, then a **separately authorized Read-Only Continuous Ledger Audit**.
3. **Clean audit still does not auto-enable S1 or capacity.**
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.** **Capacity remains 0.**

---

## Section 4 — Artifact Class Authority Ledger (template, to be completed later)

No artifact is asserted as authority now. A future storage/export charter / implementation must map
each class into this structure (documentation-only here):

| Class | Role | Provenance-bound | Authority | Status |
|-------|------|------------------|-----------|--------|
| raw_ledger | evidence | yes (active run) | none | append-only, read-only audit pending |
| s1_ledger | evidence | PENDING | none | BLOCKED |
| sqlite_wal_file | storage | PENDING | none | non-authoritative |
| append_log | evidence | PENDING | none | non-authoritative |
| audit_report | observation | PENDING | none | BLOCKED (audit unstarted) |
| json_export | artifact | PENDING | none | BLOCKED |
| csv_export | artifact | PENDING | none | BLOCKED |
| manifest_checksum | integrity | PENDING | none | non-authoritative |
| cache | derived | PENDING | none | non-authoritative |
| backup_snapshot | evidence | PENDING | none | BLOCKED |
| stdout_stderr_log | observation | PENDING | none | non-authoritative |
| generated_markdown_doc | artifact | PENDING | none | non-authoritative |
| external_upload_sync | target | PENDING | none | BLOCKED |

Every class is **non-authoritative**; the active raw ledger remains append-only with a read-only
audit still pending and unauthorized.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this storage / persistence / artifact export authority boundary charter.
2. Next **docs-only** gate may be a Monitoring / Alerting / Notification Non-Authority Boundary
   Charter.
3. Runtime / actionable gate remains: bounded raw-only 24h run completion / stop → separately
   authorized Read-Only Continuous Ledger Audit. Clean audit does not auto-enable S1 or capacity.

## Post-state

- Storage / Persistence / Artifact Export Authority Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
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
- Capacity: **0**.
