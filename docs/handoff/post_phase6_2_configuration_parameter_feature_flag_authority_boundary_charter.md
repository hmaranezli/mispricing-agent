# Post-Phase 6.2 Configuration / Parameter / Feature-Flag Authority Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future configuration, parameters,
  CLI flags, environment toggles, feature flags, defaults, and policy knobs. **No** configuration
  value, feature flag, parameter, default, env var, CLI arg, or scheduler setting may create
  authority, actionability, S1 append, runtime activation, or capacity.
- It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It **does not read or mutate live config files**, **does not create feature flags**, **does not
  inspect** secrets / env vars / credentials / tokens / cookies / API keys / account balances.
- It performs **no** network request, **no** external service call, **no** test run.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, paper / canary / live, halt / restart / rollback / recovery, routing, orders,
  fills, cancels, sizing, allocation, capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Model / Agent Output Non-Authority Boundary Charter: RATIFIED at `ff0fa0f`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Halt / restart / rollback / recovery: BLOCKED.**
- **Secrets / credentials / wallet / signing / capital authority: BLOCKED.**
- **External dependency / third-party service authority: BLOCKED.**
- **Model / agent authority: BLOCKED.**
- **Configuration / parameter / feature-flag authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `ff0fa0f5306f1dd3acec9a6e7239dd1dc0a36651`.
- Parent chain:
  - `ff0fa0f5306f1dd3acec9a6e7239dd1dc0a36651` = **RATIFIED** Model / Agent Output Non-Authority
    Boundary Charter.
  - `4742d8c70417e67d1888c7394e36a0ae7aed7072` = **RATIFIED** External Dependency / Third-Party
    Service Boundary Charter.
  - `bc145f52ff130bfc35aa84ee87ba3bf60138541b` = **RATIFIED** Secrets / Credentials / Access
    Authority Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **configuration / parameter / feature-flag authority**
  boundary. It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Constitutional Anchoring (binding floors)

The existing constitution (`CLAUDE.md`) already pins the highest-risk knobs; this charter treats
them as immutable floors:

- `DRY_RUN=True` is the default and may only be set to `False` by explicit human written command —
  no flag, env var, or default may flip it autonomously.
- `config.py` guardrail constants (limits, thresholds, `DRY_RUN`, `HUMAN_APPROVAL_USD`) are
  **immutable without human action** and are **never** changed by this assistant.
- Risk limits (≤ 5% per trade, ≤ 5 open positions, 10% daily-loss halt) are floors a future
  config charter may only tighten.

## Section 3 — Boundary Gates

### Gate A — Future-Only Configuration Authority Boundary

1. This charter defines **requirements only**.
2. It **does not inspect** config / env.
3. It **does not create** parameters or feature flags.
4. It **does not authorize** runtime, S1 append, trading, paper / canary / live, recovery, routing,
   or capacity.

### Gate B — Preconditions Before Future Configuration / Parameter Work

Future config / parameter work requires:

1. Operator Authorization boundary **ratified**;
2. Secrets / Credentials / Access Authority boundary **ratified**;
3. Model / Agent Output Non-Authority boundary **ratified**;
4. an **exact future operator command**;
5. the **exact target config / parameter / flag class**;
6. the **exact allowed files / subsystem**;
7. the **exact forbidden actions**;
8. the **explicit S1 append state**;
9. the **explicit capacity state**;
10. the **explicit paper / canary / live state**;
11. **DIRTY state blocks implementation** unless the task is **documentation-only**.

### Gate C — Configuration Class Taxonomy

Future classification must define a closed taxonomy covering at least:

- **static repository config**;
- **runtime config**;
- **environment variables**;
- **CLI arguments**;
- **feature flags**;
- **scheduler parameters**;
- **risk parameters**;
- **calibration parameters**;
- **validation thresholds**;
- **service endpoint parameters**;
- **credential references**;
- **kill-switch parameters**;
- **capacity parameters**.

Each config item must map to exactly one class; an unclassifiable item is treated as the most
restrictive applicable class and **fails closed**.

### Gate D — Configuration Is Not Authority

Future systems must prove:

- **config presence does not imply authorization.**
- **env var presence does not imply authorization.**
- **CLI flag presence does not imply authorization.**
- **feature flag true does not imply runtime activation.**
- **risk parameter presence does not imply capacity.**
- **endpoint parameter presence does not imply external-service authority.**
- **credential reference presence does not imply credential use.**
- **kill-switch parameter presence does not imply halt / restart authority.**
- **scheduler parameter presence does not imply execution authority.**
- **default value presence does not imply safe operation.**

### Gate E — Default and Implicit-Value Fail-Closed Doctrine

Future systems must **fail closed** for:

- missing explicit parameter;
- implicit default;
- empty value;
- whitespace value;
- ambiguous value;
- stale parameter;
- conflicting parameter;
- type-coerced parameter;
- float where `Decimal` / `int` is required;
- unknown feature flag;
- config value not bound to provenance.

The default in every missing or ambiguous state is the **safe / blocked** outcome — never a
permissive fallback.

### Gate F — Parameter Provenance and Audit Requirements

Future parameter / config records must be:

- **operator-command-bound**;
- **commit / base-SHA-bound**;
- **exact-file / path-bound** where applicable;
- **artifact-hash-bound** where persisted;
- **timestamped**;
- **type-explicit** (`Decimal` / `int` / `str` / `bool` declared, never inferred);
- **source-authority-bound**;
- **deterministic and reproducible**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only);
- **stored only in a separately authorized mechanism** (this charter creates no such store).

### Gate G — Feature-Flag Firewall

1. **Feature flags require a separate future charter** before implementation.
2. Feature flags must **not auto-enable S1 append**.
3. Feature flags must **not auto-enable paper / canary / live**.
4. Feature flags must **not auto-enable trading / actionability**.
5. Feature flags must **not auto-enable capacity**.
6. Feature flags must **not bypass operator authorization**.
7. **Unknown or stale feature flag state fails closed.**
8. **No agent / model / scheduler / background process may flip authority-bearing flags.**

### Gate H — Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `config file ⇒ runtime authorization`
- `env var ⇒ credential authority`
- `CLI flag ⇒ S1 append`
- `feature flag ⇒ live mode`
- `risk parameter ⇒ capacity`
- `calibration parameter ⇒ signal`
- `validation threshold ⇒ trade`
- `scheduler parameter ⇒ execution`
- `endpoint config ⇒ external authority`
- `default value ⇒ safe state`
- `config drift ⇒ automatic recovery`
- `model-generated config ⇒ authority`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** config read.
3. **No** config write.
4. **No** env inspection.
5. **No** parameter creation.
6. **No** feature-flag creation.
7. **No** executable policy.
8. **No** S1 append.
9. **No** production stream.
10. **No** signal / trade / order / routing / capital output.
11. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future configuration / parameter **TDD** requires a separate explicit operator command.
2. Future configuration / parameter **implementation** requires a separate explicit operator
   command.
3. Future **feature-flag implementation** requires a separate explicit charter and command.
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.**
6. **Capacity remains 0.**

---

## Section 4 — Configuration Class Authority Ledger (template, to be completed later)

No config value is asserted now. A future configuration charter / implementation must map each
class into this structure (documentation-only here; **never** record a secret value):

| Config class | Authority | Provenance-bound | Fail-closed on missing | Status |
|--------------|-----------|------------------|------------------------|--------|
| static_repository_config | none | PENDING | yes | non-authoritative |
| runtime_config | none | PENDING | yes | non-authoritative |
| environment_variables | none | PENDING | yes | non-authoritative |
| cli_arguments | none | PENDING | yes | non-authoritative |
| feature_flags | none | PENDING | yes | BLOCKED |
| scheduler_parameters | none | PENDING | yes | non-authoritative |
| risk_parameters | none | PENDING | yes | BLOCKED (capacity 0) |
| calibration_parameters | none | PENDING | yes | BLOCKED |
| validation_thresholds | none | PENDING | yes | non-authoritative |
| service_endpoint_parameters | none | PENDING | yes | read-only raw collection only |
| credential_references | none | PENDING | yes | BLOCKED |
| kill_switch_parameters | none | PENDING | yes | BLOCKED |
| capacity_parameters | none | PENDING | yes | BLOCKED (capacity 0) |

Every class is **non-authoritative**; `config.py` guardrail constants remain immutable without
human action.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this configuration / parameter / feature-flag authority boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command: a separate config/parameter TDD charter, then a
   RED→GREEN implementation.
4. Feature-flag implementation remains behind its **own** separate charter and operator command.

## Post-state

- Configuration / Parameter / Feature-Flag Authority Boundary Charter: **BUILT / RATIFIABLE /
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
- Capacity: **0**.
