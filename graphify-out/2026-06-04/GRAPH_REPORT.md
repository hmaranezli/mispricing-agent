# Graph Report - mispricing_agent  (2026-06-03)

## Corpus Check
- 95 files · ~67,325 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1321 nodes · 2039 edges · 89 communities (84 shown, 5 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8b89333f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]

## God Nodes (most connected - your core abstractions)
1. `scan_edges()` - 39 edges
2. `verify()` - 29 edges
3. `_monitor_positions()` - 26 edges
4. `fair_yes()` - 25 edges
5. `risk()` - 24 edges
6. `redteam()` - 22 edges
7. `_heal_pending_resolutions()` - 21 edges
8. `parse_market_window()` - 21 edges
9. `_scan_and_execute()` - 20 edges
10. `main()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_current_price_btc_is_positive()` --calls--> `current_price()`  [EXTRACTED]
  tests/test_hl_candles.py → data/hl_candles.py
- `test_current_price_eth_is_positive()` --calls--> `current_price()`  [EXTRACTED]
  tests/test_hl_candles.py → data/hl_candles.py
- `execute()` --calls--> `execute()`  [EXTRACTED]
  main_loop.py → execution/clob_executor.py
- `execute()` --calls--> `execute()`  [EXTRACTED]
  main_loop.py → execution/executor.py
- `_run_council()` --calls--> `gate()`  [EXTRACTED]
  main_loop.py → council/gate.py

## Communities (89 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (20): parse_market_window(), Ham Gamma market dict'inden scout'un ihtiyacı olan alanları çıkarır.     Returns, endDate yoksa None döner., negRisk=True doğru parse edilir., negRisk alanı yoksa False varsayılır., Dönen marketlerde parse_market_window çalışıyor (None dönmeyenlerde alanlar var), Tüm alanlar dolu market dict'inden doğru çıkarım., Gelecekteki bir market için seconds_remaining > 0. (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (43): _asset_of(), str, Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner., Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner., scan_edges(), main(), council/verifier.py — KATMAN 2: Bağımsız Doğrulayıcı.  Scout bulgusunu taze API, tests/test_scout.py — council/scout.py testleri. Unit testler (_asset_of, _edge_ (+35 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (39): 10. Bağımlılıklar, 1. Amaç, 2. Arayüz, 3. Finding Yapısı (scout çıktısı — referans), 4. Guard Sırası, 5. Giriş Fiyatı Hesabı, 6. Pozisyon Kaydı (dönüş değeri), 7. JSONL Log (+31 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (33): tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu., positions tablosu ref_price ve edge sütunlarına sahip olmalı., log_position_open ref_price ve edge değerlerini DB'ye yazar., positions tablosu realized_pnl sütununa sahip olmalı., Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.     entry=0.40, exit=0, pm_exit_price=None (market_expired) → realized_pnl=None., init_schema sonrası candidates ve positions tabloları var., positions tablosu shares, order_id, yes_token_id, no_token_id sütunlarına sahip (+25 more)

### Community 4 - "Community 4"
Cohesion: 0.21
Nodes (15): float, Açık pozisyonun token'larını satar (IOC SELL order).      pos: position dict — a, sell_position(), _open_pos(), tests/test_position_store.py — sell_position() testleri., YES pozisyon → yes_token_id kullanılır, side=SELL., NO pozisyon → no_token_id kullanılır., Başarılı SELL → float fill fiyatı döner. (+7 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (36): fair_yes(), float, str, data/fair_value.py — Binary option fair value hesaplayıcı. Model: log-normal GBM, P(asset_price > p_ref at resolution | current_price = p_now)      Args:, tests/test_fair_value.py — data/fair_value.py unit testleri Gerçek API çağrısı y, Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var ve pozitif., ETH daha yüksek vol kullandığı için aynı sapmayla daha geniş dağılım. (+28 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (37): bool, bool, float, str, _result(), current_price(), Şimdiki HL fiyatını döner (son 1m mumun close fiyatı)., _fake_finding() (+29 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (27): fetch_candles(), fetch_candles_range(), main(), price_at_timestamp(), float, int, str, data/hl_candles.py — Hyperliquid'den GERCEK gecmis fiyat (candle) ceker. Uydurma (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (35): _fee_adjusted_edge(), _parse_taker_fee(), bool, float, str, Gamma takerBaseFee → ondalık oran.     Polymarket %2 fee → takerBaseFee=1000 → 1, Fee sonrası gerçek edge.     YES: fair × (1−fee) − ask     NO:  (1−fair) × (1−fe, _result() (+27 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (41): check_exit(), close_position(), _log(), float, int, Path, str, position/manager.py — Açık pozisyon takibi ve çıkış kararı. (+33 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (38): execute(), _log(), Path, str, execution/executor.py — DRY_RUN order logger., Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür., _finding(), _gate() (+30 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (29): Dosya Yapısı, Doğrulama, Gate Katmanı (Katman 5) Implementation Plan, Sabit Referanslar (config.py'den, değiştirme), Task 1: Skeleton + `_confidence_score()` + 4 Test, Task 2: `_gate_decide()` + 3 Test, Task 3: `_log()` + `gate()` + 3 Async Test, Task 4: `main()` + Tam Test Koşusu (+21 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (27): _kelly(), bool, float, int, str, Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0., Pozisyon boyutlandırması ve sistem limiti kontrolü.      Args:         finding:, _result() (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (23): 1. Sormadan değişiklik yok, 2. DRY_RUN varsayılan, 3. Verisiz/uydurma işlem yok (anti-hallucination), 4. Konsey onayı zorunlu, 5 katmanlı konsey (sırayla inşa edilecek), 5. Risk limitleri kutsaldır, 6. Test-önce (TDD), 7. Her şey loglanır (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.23
Nodes (24): _confidence_score(), gate(), _gate_decide(), _log(), float, 0-100 güven skoru. 4 bileşen ağırlıklı toplam., Güven skoru hesapla, CONFIDENCE_THRESHOLD kontrolü yap., Kararı LOG_FILE'a yaz. Dizin yoksa oluşturur. (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (23): Dosya Haritası, P&L Resolution Implementation Plan, Task 1: `_parse_resolution` + `fetch_resolved` — shortterm.py, Task 2: `_monitor_positions` güncelleme, Task 3: `notify_close` P&L satırı, Task 4: Tam suite + bot restart, Dosya Haritası, Realized P&L + Daily Loss Restart Recovery Implementation Plan (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.05
Nodes (44): _base_pos(), tests/test_monitor.py — monitor/ birim testleri. Sıfır gerçek HTTP/dosya., pm_exit_price yoksa P&L satırı olmaz., logs/KILL dosyası varsa check() True döner., logs/KILL dosyası yoksa check() False döner., WIN pozisyon için GÜNCELLENDİ + ✅ içeren mesaj gönderir., Token + chat_id varsa requests.post çağrılır., LOSS pozisyon için ❌ içeren mesaj gönderir. (+36 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (20): fetch_fee_rate(), _fetch_from_api(), _parse(), float, str, data/fee_rate.py — Polymarket CLOB fee rate, 5dk TTL cache ile., base_fee (bps) → ondalık. 1000 → 0.02., token_id için taker fee'yi döner. 5dk cache kullanır.     Hata durumunda DEFAULT (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (19): main(), council/gate.py — KATMAN 5: Kapı.  Son karar ve uygulama katmanı. 4 katmandan ge, Manuel test: Scout→Verifier→RedTeam→Risk→Gate tam zinciri., main(), council/redteam.py — KATMAN 3: Şeytan Avukatı.  "Bu işlemi neden YAPMAMALIYIZ?", Bulguya karşı şeytan avukatlığı yapar.      Args:         finding:      Scout sc, redteam(), main() (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (7): DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., test_live_monitor_calls_sell_position_on_exit()

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (17): 1. Günlük Kayıp Limiti (HALT), 2. Açık Pozisyon Limiti, 3. Edge Geçerlilik Kontrolü (çift emniyet), 4. Kelly Hesabı ve Minimum Pozisyon, 5. İnsan Onayı Bayrağı (VETO DEĞİL), Amaç, Bağımlılıklar, Dosya Yapısı (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (18): _finding(), _pass_gate(), _pass_redteam(), _pass_risk(), _pass_verify(), tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı., Aynı slug için açık pozisyon varsa _run_council çağrılmaz., findings listesinde aynı slug iki kez varsa yalnızca bir pozisyon açılır. (+10 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (16): _edge_signal(), float, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, fair > ask yeterince → YES al., bid > fair yeterince → NO al., fair ≈ fiyat → edge yok → None., Edge var ama MIN_EDGE_PCT altında → None. (MIN_EDGE_PCT=0.08) (+8 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (23): main(), main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü., check(), bool, notify_close(), notify_halt(), notify_hard_stop(), notify_open() (+15 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): 1. Genel Bakış, 2. Exit Reason Dağılımı, 3. Asset Bazında Performans, 4. Konsey Veto Dağılımı, 5. En İyi / En Kötü 3 Trade, Amaç, Dosya Yapısı, Kapsam Dışı (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.23
Nodes (10): bool, run_test(), ClobClient, get_client(), execution/clob_client.py — py-clob-client-v2 singleton. Lazy init, env'den crede, Singleton ClobClient döndür. İlk çağrıda oluşturulur., Global state'i sıfırla — test yardımcısı., reset_client() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (22): _finding(), _gate(), tests/test_clob_executor.py — clob_executor execute() testleri., v2'de takingAmount gerçek share sayısıdır — sizeFilled yoktur., sizeFilled key'i yanıtta hiç yoksa (None default) — fill_shares 0 dönmemeli., LIVE order fiyatı = best_ask + PRICE_PREMIUM olmalı — fill rate iyileştirmesi., LIVE position dict'te entry_hl_price = finding['cur_price'] olmalı., Order MATCHED → position dict döner, gerekli alanlar dolu. (+14 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (13): backfill(), get_connection(), patch_position_resolution(), float, Path, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_ (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (10): Dosya Haritası, execution/ Implementation Plan, Self-Review Notları, Task 1: `_log()` yardımcı fonksiyon, Task 2: Guard — gate fail ve max pozisyon, Task 3: execute() happy path — pozisyon kaydı, Dosya Haritası, Performance Analysis Script Implementation Plan (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (8): Dosya Haritası, Matematiksel temel, Scout Fair Value Rewrite — Implementation Plan, Sıradaki Aşama (Bu Plandan Sonra), Task A1: data/fair_value.py — Binary Option Fair Value Modeli, Task A3: data/shortterm.py — parse_market_window() ekle, Task B1: council/scout.py — Tam Rewrite (Fair Value Modeli), Verification Checklist (Tamamlama Öncesi)

### Community 31 - "Community 31"
Cohesion: 0.20
Nodes (9): 6 Kontrol, Amaç, Dosya Değişiklikleri, Eşik Sabitleri (redteam.py içinde), Fee Hesabı, RedTeam (Katman 3) — Tasarım Dokümanı, Sorumluluk Sınırı, Test Stratejisi (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.20
Nodes (9): tests/test_balance.py — get_effective_bankroll testleri., DRY_RUN=True → config bankroll döner, API çağrısı yok., DRY_RUN=False → gerçek bakiye mikro-USDC'den dönüştürülür., Bakiye > config → config döner (güvenlik üst sınırı)., API hatası → config bankroll fallback, sistem durmuyor., test_dry_run_returns_config(), test_live_api_error_falls_back_to_config(), test_live_caps_at_config() (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.12
Nodes (19): float, int, _daily_loss_usd(), Finding'i 5 katmandan geçirir. Herhangi biri düşerse None., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar. (+11 more)

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (7): Dosya Haritası, Fonksiyon İmzaları (referans), main_loop Implementation Plan, Self-Review, Task 1: `main_loop.py` iskeleti + `_run_council()`, Task 2: `_scan_and_execute()`, Task 3: `_monitor_positions()`

### Community 35 - "Community 35"
Cohesion: 0.25
Nodes (7): Dosya Haritası, position/ Implementation Plan, Referans: Test Sabitleri, Self-Review, Task 1: `_log()` + `close_position()`, Task 2: `check_exit()` — zaman ve expiry kontrolleri, Task 3: `check_exit()` — thesis ve kâr hedefi

### Community 36 - "Community 36"
Cohesion: 0.25
Nodes (7): tests/test_clob_client.py — clob_client singleton testleri., POLY_PRIVATE_KEY yoksa get_client() KeyError verir., get_client() iki kez çağrılınca aynı nesneyi döndürür., reset_client() sonrası get_client() yeni nesne oluşturur., test_get_client_raises_when_env_missing(), test_get_client_returns_singleton(), test_reset_client_clears_singleton()

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (17): _heal_pending_resolutions(), market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., Heal başarılıysa notify_resolved_late doğru asset/seq_no ile çağrılır. (+9 more)

### Community 38 - "Community 38"
Cohesion: 0.36
Nodes (7): _make_pos(), DRY_RUN=True → hiçbir şey yapmaz, 0 checked., Market kapanmış (window=None) + çözüm var → pozisyon kapatılır., Market hâlâ açık (window mevcut) → pozisyona dokunulmaz., test_reconcile_active_market_not_closed(), test_reconcile_closes_resolved_market(), test_reconcile_skips_in_dry_run()

### Community 39 - "Community 39"
Cohesion: 0.43
Nodes (6): fetch_market_state(), main(), _post(), data/hyperliquid.py — Hyperliquid veri katmani (public, key gerekmez). BTC/ETH i, Basit yon gostergesi: mark vs oracle + gunluk degisim + funding., _signal()

### Community 40 - "Community 40"
Cohesion: 0.29
Nodes (6): Dosya Haritası, market_expired Heal — Implementation Plan, Task 1: `patch_position_resolution()` — DB Patch Fonksiyonu, Task 2: Retroaktif Backfill Script, Task 3: `_heal_pending_resolutions()` — Yapısal Fix, Task 4: Verification — Strateji Analizine Hazırlık

### Community 41 - "Community 41"
Cohesion: 0.53
Nodes (5): fetch_crypto_markets(), _fmt(), main(), _parse(), data/polymarket.py — Polymarket veri katmani (ADIM 1: canli fiyat cekme) Gamma A

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (5): Dosya Haritası, monitor/ Implementation Plan, Task 1: monitor/notifier.py — 6 test, Task 2: monitor/kill_switch.py — 2 test, Task 3: main_loop.py entegrasyonu — mevcut 6 test kırılmaz

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (5): Dosya Haritası, Task 1: Scout'a slug ekle, Task 2: council/verifier.py — Bağımsız Doğrulayıcı, Verification Checklist (Tamamlama Öncesi), Verifier (Katman 2) Implementation Plan

### Community 44 - "Community 44"
Cohesion: 0.40
Nodes (4): Dosya Haritası, RedTeam (Katman 3) Implementation Plan, Task 1: council/redteam.py — Şeytan Avukatı, Verification Checklist

### Community 45 - "Community 45"
Cohesion: 0.11
Nodes (23): build_stats_message(), int, tests/test_telegram_commands.py — Telegram komut sistemi testleri., breakeven>0 iken 'Berabere' satırı mesaja eklenmeli., breakeven=0 iken 'Berabere' satırı görünmemeli., Win rate = wins/(wins+losses) — expired ve berabere dahil edilmez., Berabere=0 iken win rate değişmez — geriye dönük uyumluluk., Yanlis chat_id → False (+15 more)

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (6): Dosya Haritası, Dynamic Bankroll Implementation Plan, Risk Notları, Task 1: `execution/balance.py` — Failing Test Yaz, Task 2: `execution/balance.py` — İmplementasyon Yaz, Task 3: `main_loop.py` — Dinamik Bankroll Entegrasyonu

### Community 57 - "Community 57"
Cohesion: 0.20
Nodes (9): Dosya Haritası, Fee Rate + Pozisyon Mutabakatı İmplementasyon Planı, Self-Review, Task 1: `data/fee_rate.py` — Failing Test, Task 2: `data/fee_rate.py` — İmplementasyon, Task 3: Scout → Fee'yi Finding'e Ekle, Task 4: `execution/reconcile.py` — Failing Test, Task 5: `execution/reconcile.py` — İmplementasyon (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.13
Nodes (14): Dosya Haritası, Polymarket CLOB API Entegrasyonu — Implementation Plan, Sonraki Adım: Aşama 2 (DRY_RUN=False), Step 1: Failing test yaz, Step 1: Failing testleri yaz, Task 1: requirements.txt + py-clob-client kurulumu, Task 2: DB Schema — 4 Yeni Kolon + logger güncelleme, Task 3: council/scout.py — yes_token_id + no_token_id finding'e ekle (+6 more)

### Community 59 - "Community 59"
Cohesion: 0.08
Nodes (23): Adım 1.1 — shortterm.py'e parse yardımcısı ekle, Adım 1.2 — scout.py'deki bug'ı düzelt, Adım 1.3 — Test yaz ve çalıştır, Adım 1.4 — Commit, Adım 2.1 — approve_usdc.py'yi komple yeniden yaz, Adım 2.2 — Commit, Adım 3.1 — requests[socks] kur, Adım 3.2 — Cloudflare WARP kur (ücretsiz yol) (+15 more)

### Community 60 - "Community 60"
Cohesion: 0.08
Nodes (23): 3 Aşamalı Rollout, Aşama 1 — API Bağlantı Testi (DRY_RUN=True), Aşama 2 — Mikro Canlı (DRY_RUN=False, BANKROLL_USD=50), Aşama 3 — Tam Deployment, Bağımlılık, clob_client.py, clob_executor.py — Entry (BUY), Credentials Yapısı (+15 more)

### Community 61 - "Community 61"
Cohesion: 0.14
Nodes (13): 6a: _load_open_positions — entry_hl_price SELECT, 6b: _monitor_positions — exit_hl_price geçir, 6c: _heal_pending_resolutions — HL fiyatları, Dosya Haritası, HL Fiyat Bildirimleri + Fill Rate İyileştirme, Task 1: Schema Migration, Task 2: db/logger.py Güncellemeleri, Task 3: execution/executor.py — DRY_RUN entry_hl_price (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.27
Nodes (9): fetch_by_slug(), fetch_resolved(), Tek slug için bağımsız sorgu — main_loop._monitor_positions kullanır., Kapanmış market için resolution fiyatlarını döndürür.      Returns: {"yes_exit":, Kapanmış market için resolution fiyatlarını döndürür.      Returns: {"yes_exit":, log_position_close(), execution/reconcile.py — LIVE startup pozisyon mutabakatı., LIVE startup: DB'deki açık pozisyonları Polymarket ile karşılaştırır.     DRY_RU (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (17): log_position_open(), _load_open_positions(), DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, DB'de açık pozisyon yoksa boş liste döner., DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır. (+9 more)

### Community 64 - "Community 64"
Cohesion: 0.25
Nodes (8): main(), _process_market(), council/scout.py — KATMAN 1: Keşif Ajanı.  Edge tanımı (matematiksel):   fair_ye, Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., _parse_token_ids(), str, clobTokenIds alanını her zaman list[str] döndür. JSON string veya list kabul ede

### Community 65 - "Community 65"
Cohesion: 0.25
Nodes (8): _calc_shares(), execute(), float, price × shares'in tam olarak ≤2 decimal olduğu en yüksek hassasiyeti döndür., price × shares'in tam olarak ≤2 decimal olduğu en yüksek hassasiyeti döndür., Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa No, Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa No, Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa No

### Community 66 - "Community 66"
Cohesion: 0.40
Nodes (4): get_effective_bankroll(), float, execution/balance.py — Etkili bankroll: DRY_RUN→config, LIVE→gerçek USDC bakiyes, DRY_RUN=True  → bankroll_config (env değeri), API çağrısı yok.     DRY_RUN=False

### Community 67 - "Community 67"
Cohesion: 0.40
Nodes (5): execute(), DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir.

### Community 68 - "Community 68"
Cohesion: 0.40
Nodes (5): poll_commands(), Ana bot ile birlikte asyncio.create_task() ile calisir., Ana bot ile birlikte asyncio.create_task() ile calisir., Ana bot ile birlikte asyncio.create_task() ile calisir., Ana bot ile birlikte asyncio.create_task() ile calisir.

### Community 69 - "Community 69"
Cohesion: 0.40
Nodes (5): fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., test_heal_fixes_null_pnl_when_api_returns()

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (23): on_trade_closed(), float, str, monitor/circuit_breaker.py — Akilli devre kesici: bankroll korumasi + streak tak, Her trade kapanisinda cagrilir.      Returns:         'hard_stop'  → bankroll %5, hard_pause(), soft_pause(), tests/test_circuit_breaker.py — monitor/circuit_breaker.py testleri. (+15 more)

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (13): bool, run_canary(), _fetch_slug(), find_shortterm(), main(), data/shortterm.py — Kisa vadeli BTC/ETH Up/Down market bulucu. Slug'i o anki UTC, Su an ve son birkac periyodun slug'larini uretir., Su an ve son birkac periyodun slug'larini uretir. (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (12): _parse(), tests/test_shortterm.py — data/shortterm.py testleri. parse_market_window unit t, slugs_for_now her interval için btc/eth/sol/xrp içermeli., Her asset için en az 7 pencere sorgulanmalı., fetch_by_slug(slug) — session parametresi olmadan çağrılabilmeli (main_loop kull, test_fetch_by_slug_takes_single_arg(), test_parse_invalid(), test_parse_json_string() (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.17
Nodes (11): Dosya Haritası, Smart Circuit Breaker Implementation Plan, Task 1: State Modülü (`monitor/state.py`), Task 2: Circuit Breaker Testleri (RED), Task 3: Circuit Breaker Implementasyonu (GREEN), Task 4: Notifier Güncellemesi, Task 5: Telegram Commands Güncelleme (`/hardbaslat`), Task 6: Config Güncellemesi (+3 more)

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (3): float, monitor/positions_cache.py — main_loop ve telegram_commands arasinda paylasilan, seconds_since_update()

### Community 83 - "Community 83"
Cohesion: 0.25
Nodes (9): _parse_resolution(), Market dict'inden YES/NO resolution fiyatlarını çıkarır., Market dict'inden YES/NO resolution fiyatlarını çıkarır., outcomePrices["1","0"] → yes_exit=1.0, no_exit=0.0., outcomePrices["0","1"] → yes_exit=0.0, no_exit=1.0., outcomePrices alanı yoksa None döner., test_parse_resolution_down_wins(), test_parse_resolution_missing_prices_returns_none() (+1 more)

### Community 84 - "Community 84"
Cohesion: 0.41
Nodes (11): _by_asset(), _by_exit_reason(), main(), _overview(), _pct(), int, str, run() (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.18
Nodes (10): log_candidate(), bool, str, db/logger.py — Aday ve pozisyon kayıtları. conn=None → sessiz atla., init_schema(), db/schema.py — SQLite şeması ve başlatma., conn(), positions tablosunda entry_hl_price ve exit_hl_price kolonları olmalı. (+2 more)

### Community 86 - "Community 86"
Cohesion: 0.18
Nodes (11): Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır. (+3 more)

### Community 87 - "Community 87"
Cohesion: 0.10
Nodes (26): _monitor_positions(), Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır. (+18 more)

### Community 88 - "Community 88"
Cohesion: 0.24
Nodes (11): arm(), disarm(), monitor/kill_switch.py — Dosya tabanlı kill switch. touch logs/KILL → durur., hard_resume(), monitor/state.py — Paylasilan bot durumu: main_loop ve telegram_commands arasin, soft_resume(), handle_command(), _query_daily_pnl() (+3 more)

### Community 89 - "Community 89"
Cohesion: 0.18
Nodes (11): build_durum_message(), is_authorized(), bool, float, str, /durum acik pozisyon yoksa bos mesaj vermemeli, /durum mesaji acik pozisyon sayisi icermeli, /durum acik pozisyon yoksa bos mesaj vermemeli (+3 more)

### Community 90 - "Community 90"
Cohesion: 0.29
Nodes (7): load_closed_today(), Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., load_closed_today yalnızca bugünün UTC kapanışlarını döndürür, önceki günleri de, test_load_closed_today_returns_only_todays()

### Community 91 - "Community 91"
Cohesion: 0.33
Nodes (5): Değişen Dosyalar, Heal Notification + İstatistik Berabere Fix Implementation Plan, Task 1: notify_resolved_late fonksiyonu, Task 2: _heal_pending_resolutions notify çağrısı, Task 3: /istatistik berabere fix

### Community 92 - "Community 92"
Cohesion: 0.20
Nodes (10): parse_hours(), /istatistik6' → 6  |  '/istatistik' → None, /istatistik6' → 6  |  '/istatistik' → None, /istatistik → None (tum zamanlar), /istatistikABC → None (sayisal degil), test_parse_hours_12_returns_12(), test_parse_hours_24_returns_24(), test_parse_hours_6_returns_6() (+2 more)

### Community 94 - "Community 94"
Cohesion: 0.18
Nodes (11): fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır. (+3 more)

### Community 97 - "Community 97"
Cohesion: 0.67
Nodes (3): /baslat SOFT_PAUSED'u temizler., /baslat SOFT_PAUSED'u temizler., test_baslat_clears_soft_paused()

### Community 98 - "Community 98"
Cohesion: 0.67
Nodes (3): /hardbaslat HARD_PAUSED'u temizler., /hardbaslat HARD_PAUSED'u temizler., test_hardbaslat_clears_hard_paused()

## Knowledge Gaps
- **286 isolated node(s):** `restart.sh script`, `str`, `int`, `PreToolUse`, `allow` (+281 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `poll_commands()` connect `Community 68` to `Community 88`, `Community 89`, `Community 23`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `scan_edges()` connect `Community 1` to `Community 64`, `Community 33`, `Community 6`, `Community 8`, `Community 79`, `Community 18`, `Community 23`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `verify()` connect `Community 18` to `Community 0`, `Community 1`, `Community 33`, `Community 5`, `Community 6`, `Community 8`, `Community 23`, `Community 62`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **What connects `restart.sh script`, `main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü.`, `DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir.` to the rest of the system?**
  _682 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.11052631578947368 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06767676767676768 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.047619047619047616 - nodes in this community are weakly interconnected._