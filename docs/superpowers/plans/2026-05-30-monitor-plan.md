# monitor/ Implementation Plan

**Goal:** Telegram bildirim + kill switch. Notify çağrıları `main()` içinde — sub-fonksiyonlar saf kalır.

## Dosya Haritası
| Dosya | İşlem |
|-------|-------|
| `monitor/__init__.py` | Oluştur (boş) |
| `monitor/notifier.py` | Oluştur — send_telegram, notify_open/close/halt |
| `monitor/kill_switch.py` | Oluştur — check(), arm(), disarm() |
| `main_loop.py` | Güncelle — kill switch + notify entegrasyonu |
| `tests/test_monitor.py` | Oluştur — 8 test |

## Task 1: monitor/notifier.py — 6 test
- send_telegram: token varsa requests.post çağrılır, yoksa no-op
- DRY_RUN=True → mesaj başı "[DRY RUN]"
- notify_open, notify_close, notify_halt format testleri

## Task 2: monitor/kill_switch.py — 2 test
- check(): logs/KILL dosyası varsa True, yoksa False
- arm()/disarm() test yardımcıları

## Task 3: main_loop.py entegrasyonu — mevcut 6 test kırılmaz
- Döngü başı: kill_switch_check() → True ise notify_halt + break
- _monitor sonrası: newly_closed → notify_close
- _scan sonrası: newly_opened → notify_open
