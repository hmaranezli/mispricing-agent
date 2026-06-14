"""tests/test_restart_sh.py — D#8 restart.sh wiring: tmux self-kill footgun preflight (TDD).

KÖK SORUN: restart.sh `tmux kill-session -t mispricing` yapıyor; operatör/Claude oturumu DA
"mispricing" session'ındaysa o oturum ölür (footgun). Guard mantığı `monitor/restart_guard.py`'de
(check_restart_safe + detect_current_tmux_session + main CLI) test'li ve mevcut; bu test onun
restart.sh'e ENTEGRE edildiğini (preflight kill-session ÖNCESİNDE) uçtan uca kanıtlar.

HERMETİK PATH-shim harness — GERÇEK tmux/kill/pgrep ÇALIŞTIRILMAZ:
  - fakebin/tmux: tüm çağrıları log'a yazar; `display-message -p '#S'`→"mispricing" (footgun senaryosu),
    `has-session`→exit 0 (session var), `kill-session`/`new-session`→yalnız log (no-op).
  - fakebin/pgrep: boş + exit 0 (çalışan process yok → kill koluna girilmez).
  - fakebin/kill: yalnız log (bash builtin önceliği nedeniyle zaten çağrılmaz; tamlık için).
  - PATH başına fakebin; TMUX env set (preflight `detect_current_tmux_session` set görsün).
  - restart.sh repo kökünden `bash` ile koşulur; içindeki gerçek python preflight, fake tmux
    display-message'ı okuyup "mispricing"→footgun→exit 1 vermeli (GREEN). main_loop.py ASLA çalışmaz.

GÜVENLİ (GREEN) DAVRANIŞ: footgun session'ında restart.sh exit≠0 + tmux log'unda kill-session/
new-session YOK. İlk RED: preflight henüz YOK → restart.sh kill-session'a ilerler → log'da kill-session
→ assertion fail. Network/restart/gerçek-kill yok.
"""
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_fakebin(tmp_path: Path) -> tuple[Path, Path]:
    """fakebin dizini + tmux çağrı log'u oluştur. (fakebin, tmux_log) döner."""
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    tmux_log = tmp_path / "tmux_calls.log"

    # fake tmux: her çağrıyı log'a yaz; display-message → "mispricing"; has-session → 0.
    _write_exec(fakebin / "tmux", f"""#!/usr/bin/env bash
echo "$@" >> "{tmux_log}"
case "$1" in
  display-message) echo "mispricing" ;;   # footgun: içinde bulunulan session == hedef
  has-session)     exit 0 ;;               # session var (kill-session koluna girilsin)
  *)               exit 0 ;;               # kill-session / new-session / diğer → yalnız log
esac
""")
    # fake pgrep: çalışan process yok → boş çıktı, exit 0.
    _write_exec(fakebin / "pgrep", "#!/usr/bin/env bash\nexit 0\n")
    # fake kill: yalnız log (gerçek kill yok). bash builtin önceliği nedeniyle muhtemelen çağrılmaz.
    _write_exec(fakebin / "kill", f'#!/usr/bin/env bash\necho "kill $@" >> "{tmux_log}"\nexit 0\n')
    return fakebin, tmux_log


def test_restart_sh_refuses_and_skips_kill_session_when_in_target_session(tmp_path):
    """Footgun session'ında (TMUX set + tmux #S == hedef) restart.sh REDDETMELİ:
    exit≠0 + tmux kill-session/new-session ÇAĞRILMAMALI. Gerçek tmux/kill yok (PATH-shim).
    İlk RED: preflight yok → kill-session log'a düşer → assertion fail."""
    fakebin, tmux_log = _make_fakebin(tmp_path)

    env = dict(os.environ)
    env["PATH"] = f"{fakebin}{os.pathsep}" + env.get("PATH", "")
    env["TMUX"] = "/tmp/tmux-fake/default,1,0"   # tmux içindeymiş gibi → preflight tespit etsin

    proc = subprocess.run(
        ["bash", "restart.sh"], cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=30)

    log = tmux_log.read_text() if tmux_log.exists() else ""
    # PRIMARY footgun kanıtı: kendi session'ını öldürecek kill-session ASLA çağrılmamalı.
    assert "kill-session" not in log, \
        f"footgun: restart.sh kendi session'ında kill-session çağırdı (preflight yok)\nlog:\n{log}"
    assert "new-session" not in log, \
        f"footgun: restart.sh yeni session başlattı (abort etmeliydi)\nlog:\n{log}"
    assert proc.returncode != 0, \
        f"footgun session'ında restart.sh non-zero exit vermeli; rc={proc.returncode}\nstderr:\n{proc.stderr}"
