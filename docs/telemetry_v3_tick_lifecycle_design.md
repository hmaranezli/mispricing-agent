# Telemetry V3 — Minimal Tick-Level Lifecycle Design

**Amaç:** Gerçek stop/post-exit ölçümü. Şu an paper'lar `expired`'a kadar açık (gerçek stop hiç tetiklenmedi) → stop_saved_loss vs stop_cut_winner ayrımı YALNIZCA simülasyon. V3 bunu GERÇEK gözleme çevirir.

**Anayasa:** Model/clamp/threshold/entry/exit/TP DEĞİŞMEZ. Sadece telemetri/ölçüm. DRY_RUN + NEW_ENTRIES=False korunur. Tüm yazım fire-and-forget (non-blocking), hata→log+devam.

## Kapsam ve veri kaynağı

| Alan | Kaynak | Ek API? |
|------|--------|---------|
| time_to_mfe / time_to_mae | `_update_position_models` zaten `dd=(bid−entry)/entry` + `_mfe_peak`/`_mae_trough` tutuyor → peak/trough GÜNCELLENDİĞİ an `elapsed` (monotonic) kaydet | YOK (in-memory) |
| resolve_ts | `ts_close` + `close_reason` zaten var → resolve ise resolve_ts ayrı kolon | YOK |
| action-side bid/ask scan serisi | Monitor cycle zaten `pm_price=action bid` okuyor → her cycle (ts, bid) in-memory listeye ekle | YOK (mevcut okuma) |
| post_exit_max_favorable/adverse | Stop/TP tetiklenince paper'ı KAPATMA → "stopped_open" işaretle, monitor'da TUTMAYA devam et, resolve'a kadar mfe/mae ayrı segmentte izle | +1 book okuma/cycle/stopped-paper |
| stop_saved_loss / stop_cut_winner | gerçek stop exit_price vs resolve_exit karşılaştırması | YOK |

## DB / latency yükünü düşük tutma (kritik)

1. **Tick serisi DB'ye HER tick yazılmaz.** In-memory biriktir → paper kapanınca TEK batch yazım: ayrı tablo `paper_tick_series(paper_id, ts_offset_s, action_bid)` bulk INSERT, VEYA tek satırda downsample (peak/trough + ~10 eşit-aralık örnek). Downsample tercih (DB hafif).
2. **Sıfır ek API çoğu alan için** — monitor cycle pm_price'ı ZATEN okuyor; seri o değeri yeniden kullanır.
3. **post-exit tek ek maliyet:** stopped-but-open paper'lar resolve'a kadar monitor'da kalır → paper başına +1 book okuma/cycle. Sınırla: yalnızca shadow/paper cohort, MAX_POST_EXIT_TRACK cap.
4. **Yazım fire-and-forget** (model_telemetry pattern), scan/live loop'a bloklama yok. time_to_* ve resolve_ts in-memory → kapanışta mevcut INSERT'e 3 kolon eklenir (ekstra round-trip yok).

## En küçük güvenli patch
**Faz 1 (sıfır ek API, 3 kolon):** `shadow_positions`'a `time_to_mfe_s`, `time_to_mae_s`, `resolve_ts` ekle. `_update_position_models`'te peak/trough güncellenince `elapsed` damgala; kapanışta mevcut INSERT'e ekle. TDD + non-blocking. Bu tek başına "peak ne zaman oldu" sorusunu açar, post-exit/tick-serisi olmadan.
**Faz 2 (ayrı, daha ağır):** stopped-but-open post-exit tracking + downsample tick serisi. Faz 1 değeri kanıtlayınca.
