# H6 Sealed / Task I Discovery Blocker Handoff — 2026-06-11

> Kalıcı handoff. Hesap değişimi, SSH kopması veya Claude limiti bittiğinde **yeni oturum BU dosyayı ilk okur**, sonra git sanity yapar, sonra insana hangi geçerli seçeneğin alınacağını sorar. Tahmin/uydurma ile ilerlemez (CLAUDE.md anayasa madde 1 + 3).

## Current repo state
- `HEAD` == `origin/master` == **`08fd211`** (senkron, push tamam).
- Working tree **yalnızca eski untracked artefact'ler**: `faz1.patch`, `faz1_code.patch`, `faz1_remaining.patch`, `"how --stat 9927708"`. Bunlara **dokunulmaz**.
- Branch: `master`.

## H6 sealed chain (hepsi remote'da)
- `bba2aaa` — feat(execution): H4+H5 atomic accounting + envelope contract = **regression baseline**.
- `b326f93` — docs(task-h): H6 Step 1 traceability closure.
- `e2cd152` — chore(graphify): architecture map (graphify update, AST-only).
- `08fd211` — docs(task-h): H6 final checkpoint evidence seal.

## Regression evidence (current-session rebuild, 2026-06-11)
- H6 curated suite: **109 passed** (collect pollution yok; individual toplamı 109 == combined 109).
- H4+H5 isolated: **58 passed**.
- Extra coupled `test_mainloop_accounting.py`: **7 passed**.
- Full blanket `tests/`: **bilinçli koşulmadı** — network/env + aiosqlite teardown caveat; plan curated suite esas alındı.
- Regresyon baseline kodu `bba2aaa`'dan beri **değişmedi** (`bba2aaa..HEAD` `*.py` diff boş; yalnız docs + graphify-out).

## Task I discovery result (KRİTİK)
- **"Task I = Hard Caps" premisi repo ile DOĞRULANMIYOR.**
- Plandaki gerçek Task I: **PARTIAL fill → PARTIAL_FILLED** — `docs/superpowers/plans/2026-06-10-faz2c3-execute-intent-wiring.md:162`.
- Bu davranış **zaten H4/Task H ile kapsanmış** (kanıt: `tests/test_execute_intent_wiring.py:835` `H4-2 PARTIAL_FILL → PARTIAL_FILLED`, passed). Aynı dosyada Task J (ACCEPTED→no position) ve Task K (taking=0→CANCELLED) da "Task H kapsar" notlu.
- **"Hard Caps" diye yazılı bir görev/spec docs'ta da kodda da YOK** (`rg -ni "hard.?cap"` → 0 hit).

## Existing cap architecture (zaten kurulu — yeni iş değil)
- `MAX_TRADE_PCT` (0.05) → `config.py` + `council/risk.py:89`.
- `MAX_OPEN_POSITIONS` (5) → `council/risk.py:71`, `main_loop.py:185/208`, `execution/executor.py:44`.
- `HUMAN_APPROVAL_USD` (50) → `council/risk.py:93`, `main_loop.py:81`, `execution/executor.py:74`.
- `MAX_SLIPPAGE_CAP` ("0.03") → `execution/clob_executor.py:357`.
- `MIN_EXECUTABLE_NOTIONAL_USD` (5.0) → `council/scout.py:248`.
- Günlük kayıp / streak → `monitor/circuit_breaker` + `main_loop.py:918`.
- Not: Bu cap'ler **anayasa sabitleri** (`config.py`) — CLAUDE.md madde 1/5 ile **insan onayı olmadan dokunulmaz**.

## Decision
- **Yazılı spec olmadan yeni Hard Caps IMPLEMENTE ETME.**
- **Tanımsız Hard Caps için RED test YAZMA** (no-fake-RED + anti-hallucination ihlali).
- Geçerli sonraki seçenekler:
  1. faz2c3 **Task I/J/K'yı "Task H ile subsumed" olarak docs-only kapat** (plan hâlâ stale ise).
  2. **Faz 2c-4 reconcile / recovery-ladder resolve protokolü**'ne geç (Task H recovery son basamağındaki `emergency_pause` resolve akışı; faz2c4 plan ~satır 802).
  3. Yeni Hard Caps özelliği gerçekten isteniyorsa → **önce explicit spec/plan** yaz (hangi yeni cap: total-exposure? per-symbol? mevcutların hangisi eksik?), sonra TDD.

## Recovery instruction (yeni oturum için)
1. Bu handoff dosyasını oku.
2. Git sanity: `git rev-parse HEAD` == `origin/master` == `08fd211`; `git status --short` sadece eski artefact'ler olmalı.
3. İnsana **yukarıdaki 3 geçerli seçenekten hangisi** sorusunu sor; cevap gelmeden kod/test/docs/graphify değiştirme.

## Forbidden next actions
- Broad refactor yok.
- Varsayımdan Hard Caps implementasyonu yok.
- `git add .` yok.
- Eski artefact'leri (`faz1*.patch`, `"how --stat 9927708"`) silme yok.
- "live-ready / canlıya hazır" iddiası yok (DRY_RUN varsayılan; canlı geçiş yalnız insan yazılı komutuyla).
