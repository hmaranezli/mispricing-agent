# Runbook — Start / Stop / Restart (Mispricing Bot)

> Operatör (insan) prosedürü. D#8 production readiness gap'inin doküman parçası. Bu doküman bir
> **canlı/canary onayı DEĞİLDİR** — yalnız botu güvenli başlatma/durdurma/yeniden başlatma
> prosedürünü ve restart güvenlik mekanizmalarını anlatır. Anayasa (CLAUDE.md) bu dokümanın üstündedir.

---

## 1. Current safety status and NO-GO notes

- **Mevcut durum:** `DRY_RUN=False` (config LIVE) ama **`NEW_ENTRIES_ENABLED=False`** → canlı yeni
  entry KAPALI. Canlı (`dry_run=0`) açık pozisyon = 0.
- **D GENEL = PARTIAL / `production canary NOT approved`.** Mini-live/canary öncesi açık D maddeleri:
  D#2 (DRY_RUN→False insan kapısı), D#7 phase-2 (canlı balance/auth probe), D#9 (evidence packet),
  D#10 (bağımsız LLM verifier), D#11 (Gemini adversarial review).
- **NO-GO:** Aşağıdakiler insanın açık, yazılı komutu olmadan YAPILMAZ — `DRY_RUN=False`'a geçiş,
  `NEW_ENTRIES_ENABLED=True`, canlı order, canlı balance/withdrawal, gerçek API anahtarlarıyla probe.
- **Pre-F gate:** Master Plan F (gerçek para / ölçek) öncesinde **Pre-F money-making audit gate**
  zorunludur (model kalibrasyon + risk + edge audit). Bu runbook o gate'in yerine geçmez.

## 2. Tmux self-kill footgun

- **tmux footgun:** `restart.sh` hedef tmux session'ı (`SESSION="mispricing"`) `tmux kill-session`
  ile öldürür. Eğer operatör/Claude oturumu DA `mispricing` session'ının İÇİNDEYSE, restart.sh
  çalıştırıldığında **kendi oturumunu öldürür** (footgun).
- **Korunma:** `restart.sh` artık ilk iş olarak bir preflight çalıştırır (bkz §3). İçinde
  bulunduğun session hedefle aynıysa restart **hiçbir şey öldürmeden durur**.

## 3. restart.sh preflight behavior

restart.sh, `SESSION=` tanımından hemen sonra ve process-kill'den ÖNCE şu preflight'ı koşar:

```bash
venv/bin/python -m monitor.restart_guard --target "$SESSION"
```

- Preflight içinde bulunulan tmux session'ı `$TMUX` + `tmux display-message -p '#S'` ile tespit eder
  (`monitor/restart_guard.py::detect_current_tmux_session`) ve hedefle kıyaslar
  (`check_restart_safe`).
- **Hedef == içinde bulunulan session → `RestartFootgunError` → exit 1.** `set -e` nedeniyle
  restart.sh burada durur; `tmux kill-session`/`new-session`'a **ULAŞMAZ** → hiçbir şey öldürülmez.
- Farklı session veya tmux dışı (`$TMUX` boş, ör. ssh/cron) → güvenli, restart normal devam eder.
- **Sonuç:** restart.sh hedef session içinden çalıştırılırsa preflight kill-session öncesi durdurur.

## 4. SIGTERM/SIGINT graceful shutdown behavior

- `main()` başında `_install_shutdown_handlers()` → `monitor/shutdown.py::install_shutdown_signal_handlers()`
  SIGTERM ve SIGINT'i graceful shutdown'a bağlar.
- **SIGTERM** (restart.sh `kill $PIDS` / systemd) artık süreci **default öldürme yerine** bir
  shutdown flag set eder (`monitor.state.request_shutdown()` — RAISE etmez, fail-soft). **SIGINT**
  (Ctrl-C) de aynı yola gider.
- Ana `while True` her iterasyonda `_should_stop_for_shutdown()` (flag) kontrol eder ve set ise
  **break** eder → mevcut `finally: await conn.close()` çalışır (DB temiz kapanır). Yani
  **graceful shutdown**: çalışan iterasyon tamamlanır, sonra temiz çıkış.
- Platform `add_signal_handler` desteklemezse fail-soft atlanır (bot çalışmaya devam eder).

## 5. Safe stop procedure

1. **Tercih edilen — dosya kill-switch (anında, yeni emir bloklar):** `touch logs/KILL`. Ana loop
   `kill_switch_check()` ile bunu görür, `notify_halt` + temiz break.
2. **Graceful SIGTERM:** çalışan bot PID'ine `kill <PID>` (SIGTERM). Yukarıdaki graceful shutdown
   devreye girer; `kill -9` GEREKMEZ ve kullanılmamalıdır (finally atlanır).
3. Durduktan sonra `logs/KILL` dosyasını kaldırmayı unutma (`rm -f logs/KILL`) — aksi halde sonraki
   start anında durur.

## 6. Safe restart procedure

1. **restart.sh'i hedef session DIŞINDAN çalıştır** (ayrı bir kabuk/tmux session). Yanlışlıkla
   `mispricing` session içinden çalıştırırsan preflight (§3) seni korur ve durur.
2. `./restart.sh` — preflight → process-kill → `tmux kill-session` → `tmux new-session` (venv +
   `PYTHONUNBUFFERED=1` + log tee).
3. Restart sonrası §7 ve §8 checklist'lerini uygula.

## 7. Post-restart schema/runtime checklist

Restart sonrası (read-only doğrulama, `logs/mispricing.db`):

- [ ] `init_schema` çalıştı mı → `execution_state` tablosu VAR mı (`SELECT ... FROM execution_state`).
      Yoksa `is_emergency_paused` fail-closed → her şey paused görünür.
- [ ] `araf_resolution_shadow` tablosu VAR mı (additive migration uygulandı mı).
- [ ] `execution_state.emergency_paused = 0` mı (steady-state). 1 ise sebebi incele, manuel clear
      insan onayıyla.
- [ ] Açık `dry_run=0` pozisyon sayısı beklenen mi (canlı entry kapalıyken 0 olmalı).
- [ ] `order_intents` içinde `SUBMITTED_UNKNOWN`/`RECOVERY_REQUIRED` artığı var mı (2c-4 reconcile bekleyen).

> **post-restart schema verification** bu checklist'tir; başarısızsa botu durdur (§5) ve incele.

## 8. Post-restart smoke checks

- [ ] Log akıyor mu (`tail -f logs/main_loop.log`); `[bot] Başladı` + tarama satırları görünüyor mu.
- [ ] Tek instance mı (`pgrep -f "python.*main_loop.py" | wc -l` == 1).
- [ ] Telegram startup/restart bildirimi geldi mi (notifier env doluysa).
- [ ] WS bağlantısı/price akışı sağlıklı mı; scan funnel hata basmıyor mu.
- [ ] `NEW_ENTRIES_ENABLED` ve `DRY_RUN` beklenen değerlerde mi (config doğrulaması).

## 9. Not approved without explicit approval

Aşağıdakiler **insanın açık yazılı onayı olmadan YAPILMAZ** (anayasa madde 1/2):

- `DRY_RUN=False`'a fiili geçiş veya `NEW_ENTRIES_ENABLED=True`.
- Canlı order gönderimi, canary, mini-live.
- **no live API/Telegram/DB without approval** — gerçek API anahtarlarıyla balance/auth probe,
  canlı DB write, dışa mesaj.
- **`production canary NOT approved`** durumu geçerli; D#2/#7/#9/#10/#11 + **Pre-F** money-making
  audit gate tamamlanmadan canlıya geçilmez.

## 10. Emergency rollback / operator notes

- **Acil durdur:** `touch logs/KILL` (anında, yeni emir bloklar) + gerekiyorsa graceful SIGTERM.
- **Kod rollback:** `git log --oneline` ile son iyi commit'i bul, `git checkout <hash> -- <dosya>`
  veya branch revert; restart (§6).
- **DB güvenliği:** SQLite ACID; ani ölümde bozulma beklenmez. Şüphede `~/db_backups/` altındaki
  son `.backup()` snapshot'ından restore (D#1 drill prosedürü).
- **Emergency pause:** otomatik trip → operatör Telegram alert (D#6). Manuel clear yalnız insan
  onayıyla (`clear_emergency_pause` / resolve protokolü).
- **Footgun hatırlatma:** restart'ı hedef tmux session dışından çalıştır; şüphede preflight'a güven.
