# Graph Report - mispricing_agent  (2026-06-03)

## Corpus Check
- 93 files · ~62,222 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1244 nodes · 1929 edges · 100 communities (81 shown, 19 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f8f7fb2`
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
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
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
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]

## God Nodes (most connected - your core abstractions)
1. `scan_edges()` - 39 edges
2. `verify()` - 29 edges
3. `fair_yes()` - 25 edges
4. `risk()` - 24 edges
5. `_monitor_positions()` - 23 edges
6. `redteam()` - 22 edges
7. `parse_market_window()` - 21 edges
8. `_scan_and_execute()` - 19 edges
9. `main()` - 19 edges
10. `_heal_pending_resolutions()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_scan_edges_returns_list()` --calls--> `scan_edges()`  [EXTRACTED]
  tests/test_scout.py → council/scout.py
- `execute()` --calls--> `execute()`  [EXTRACTED]
  main_loop.py → execution/clob_executor.py
- `execute()` --calls--> `execute()`  [EXTRACTED]
  main_loop.py → execution/executor.py
- `test_load_open_positions_returns_open_ones()` --calls--> `_load_open_positions()`  [EXTRACTED]
  tests/test_main_loop.py → main_loop.py
- `_run_council()` --calls--> `gate()`  [EXTRACTED]
  main_loop.py → council/gate.py

## Communities (100 total, 19 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (17): fetch_resolved(), parse_market_window(), Kapanmış market için resolution fiyatlarını döndürür.      Returns: {"yes_exit":, Kapanmış market için resolution fiyatlarını döndürür.      Returns: {"yes_exit":, Ham Gamma market dict'inden scout'un ihtiyacı olan alanları çıkarır.     Returns, log_position_close(), execution/reconcile.py — LIVE startup pozisyon mutabakatı., LIVE startup: DB'deki açık pozisyonları Polymarket ile karşılaştırır.     DRY_RU (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.26
Nodes (12): _asset_of(), str, tests/test_scout.py — council/scout.py testleri. Unit testler (_asset_of, _edge_, test_asset_of_bitcoin(), test_asset_of_btc_short(), test_asset_of_empty_returns_none(), test_asset_of_ethereum(), test_asset_of_none_returns_none() (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (39): 10. Bağımlılıklar, 1. Amaç, 2. Arayüz, 3. Finding Yapısı (scout çıktısı — referans), 4. Guard Sırası, 5. Giriş Fiyatı Hesabı, 6. Pozisyon Kaydı (dönüş değeri), 7. JSONL Log (+31 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (28): init_schema(), conn(), tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu., positions tablosu ref_price ve edge sütunlarına sahip olmalı., log_position_open ref_price ve edge değerlerini DB'ye yazar., positions tablosu realized_pnl sütununa sahip olmalı., Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.     entry=0.40, exit=0, pm_exit_price=None (market_expired) → realized_pnl=None. (+20 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (31): bool, run_canary(), bool, run_test(), ClobClient, get_effective_bankroll(), float, execution/balance.py — Etkili bankroll: DRY_RUN→config, LIVE→gerçek USDC bakiyes (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (36): fair_yes(), float, str, data/fair_value.py — Binary option fair value hesaplayıcı. Model: log-normal GBM, P(asset_price > p_ref at resolution | current_price = p_now)      Args:, tests/test_fair_value.py — data/fair_value.py unit testleri Gerçek API çağrısı y, Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var ve pozitif., ETH daha yüksek vol kullandığı için aynı sapmayla daha geniş dağılım. (+28 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (16): _fake_finding(), council/verifier.py testleri. Gerçek API kullanılır — mock yok., Scout cur_price=1.0 (imkansız) iken HL taze fiyat ~73k → drift devasa → api_mism, seconds_remaining=0 → HL drift kontrolü sonrası expired veya fetch_error.     Sc, seconds_remaining=0 → expired veya fetch_error, halt=False.     current_price mo, Geçersiz slug → fetch_error, halt=False., Geçersiz slug → fetch_error, halt=False. HL mock'lu — rate limit'ten bağımsız., PM fetch None döndürünce finding._window fallback kullanır — fetch_error olmaz. (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (37): main(), _process_market(), council/scout.py — KATMAN 1: Keşif Ajanı.  Edge tanımı (matematiksel):   fair_ye, Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., current_price(), fetch_candles(), fetch_candles_range() (+29 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (23): _fee_adjusted_edge(), _parse_taker_fee(), bool, float, str, Gamma takerBaseFee → ondalık oran.     Polymarket %2 fee → takerBaseFee=1000 → 1, Fee sonrası gerçek edge.     YES: fair × (1−fee) − ask     NO:  (1−fair) × (1−fe, _result() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (35): check_exit(), close_position(), _log(), float, int, Path, str, position/manager.py — Açık pozisyon takibi ve çıkış kararı. (+27 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (34): execute(), _log(), Path, str, execution/executor.py — DRY_RUN order logger., Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür., _finding(), _gate() (+26 more)

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
Cohesion: 0.19
Nodes (27): _confidence_score(), gate(), _gate_decide(), _log(), main(), float, council/gate.py — KATMAN 5: Kapı.  Son karar ve uygulama katmanı. 4 katmandan ge, Manuel test: Scout→Verifier→RedTeam→Risk→Gate tam zinciri. (+19 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (23): Dosya Haritası, P&L Resolution Implementation Plan, Task 1: `_parse_resolution` + `fetch_resolved` — shortterm.py, Task 2: `_monitor_positions` güncelleme, Task 3: `notify_close` P&L satırı, Task 4: Tam suite + bot restart, Dosya Haritası, Realized P&L + Daily Loss Restart Recovery Implementation Plan (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (29): tests/test_monitor.py — monitor/ birim testleri. Sıfır gerçek HTTP/dosya., pm_exit_price yoksa P&L satırı olmaz., logs/KILL dosyası varsa check() True döner., logs/KILL dosyası yoksa check() False döner., WIN pozisyon için GÜNCELLENDİ + ✅ içeren mesaj gönderir., Token + chat_id varsa requests.post çağrılır., LOSS pozisyon için ❌ içeren mesaj gönderir., pm_exit_price=None ise P&L satırı olmadan yine de mesaj gönderir. (+21 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (20): fetch_fee_rate(), _fetch_from_api(), _parse(), float, str, data/fee_rate.py — Polymarket CLOB fee rate, 5dk TTL cache ile., base_fee (bps) → ondalık. 1000 → 0.02., token_id için taker fee'yi döner. 5dk cache kullanır.     Hata durumunda DEFAULT (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (25): main(), council/redteam.py — KATMAN 3: Şeytan Avukatı.  "Bu işlemi neden YAPMAMALIYIZ?", main(), council/risk.py — KATMAN 4: Risk Değerlendirmesi.  "Ne kadar?" sorusunu cevaplar, Manuel test: Scout→Verifier→RedTeam→Risk zincirini çalıştırır., Manuel test: Scout→Verifier→RedTeam→Risk zincirini çalıştırır., Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner., Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner. (+17 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (6): DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır., test_live_monitor_calls_sell_position_on_exit()

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (17): 1. Günlük Kayıp Limiti (HALT), 2. Açık Pozisyon Limiti, 3. Edge Geçerlilik Kontrolü (çift emniyet), 4. Kelly Hesabı ve Minimum Pozisyon, 5. İnsan Onayı Bayrağı (VETO DEĞİL), Amaç, Bağımlılıklar, Dosya Yapısı (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (18): _finding(), _pass_gate(), _pass_redteam(), _pass_risk(), _pass_verify(), tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı., Aynı slug için açık pozisyon varsa _run_council çağrılmaz., findings listesinde aynı slug iki kez varsa yalnızca bir pozisyon açılır. (+10 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (12): _edge_signal(), float, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, fair > ask yeterince → YES al., bid > fair yeterince → NO al., fair ≈ fiyat → edge yok → None., MIN_EDGE_PCT (0.08) üstünde edge → geçer. Float kesinliğinden kaçınmak için 0.10 (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (27): main(), main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü., check(), bool, notify_close(), notify_halt(), notify_hard_stop(), notify_open() (+19 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): 1. Genel Bakış, 2. Exit Reason Dağılımı, 3. Asset Bazında Performans, 4. Konsey Veto Dağılımı, 5. En İyi / En Kötü 3 Trade, Amaç, Dosya Yapısı, Kapsam Dışı (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.29
Nodes (7): log_position_open(), DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır., DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır., DRY_RUN=True → _run_council'a daily_loss_usd=0 geçilir, kayıp limiti uygulanmaz., Restart sonrası DB'den yüklenen bugünün kapanan pozisyonları _daily_loss_usd'e d, test_daily_loss_includes_recovered_closed_positions(), test_load_open_positions_returns_open_ones()

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (24): _calc_shares(), execute(), float, price × shares'in tam olarak ≤2 decimal olduğu en yüksek hassasiyeti döndür., Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa No, Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa No, _finding(), _gate() (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (12): backfill(), get_connection(), patch_position_resolution(), float, Path, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_, Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_ (+4 more)

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
Cohesion: 0.13
Nodes (17): float, int, _daily_loss_usd(), Finding'i 5 katmandan geçirir. Herhangi biri düşerse None., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar., Yeni fırsatları tarar, konsey geçenleri açar. (+9 more)

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
Cohesion: 0.10
Nodes (21): _heal_pending_resolutions(), market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., market_expired + pm_exit_price=None kayıtları için resolution retry eder., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır. (+13 more)

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
Cohesion: 0.23
Nodes (14): Bulguya karşı şeytan avukatlığı yapar.      Args:         finding:      Scout sc, redteam(), _fake_finding(), _fake_verification(), fresh_seconds=60 (< 120) → insufficient_time_for_thesis veto., fresh_edge=0.40 (> 0.35) → edge_suspiciously_large veto., fair=0.50, ask=0.43 → gross=0.07, net≈0.059 < 0.08 → veto., PM fetch None döndürünce _raw_market fallback kullanır — market_data_unavailable (+6 more)

### Community 62 - "Community 62"
Cohesion: 0.15
Nodes (13): bool, bool, float, str, _result(), _result() her zaman gerekli alanları döndürür., Soft fail'de (edge_gone, expired, fetch_error) halt=False., api_mismatch'te halt değeri HALT_ON_API_MISMATCH config'ine eşit. (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (13): execute(), _load_open_positions(), DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir., DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru (+5 more)

### Community 64 - "Community 64"
Cohesion: 0.50
Nodes (4): Edge var ama MIN_EDGE_PCT altında → None. (MIN_EDGE_PCT=0.08), NO edge ama MIN_EDGE_PCT altında → None., test_edge_signal_below_min_threshold_no(), test_edge_signal_below_min_threshold_yes()

### Community 78 - "Community 78"
Cohesion: 0.11
Nodes (23): on_trade_closed(), float, str, monitor/circuit_breaker.py — Akilli devre kesici: bankroll korumasi + streak tak, Her trade kapanisinda cagrilir.      Returns:         'hard_stop'  → bankroll %5, hard_pause(), soft_pause(), tests/test_circuit_breaker.py — monitor/circuit_breaker.py testleri. (+15 more)

### Community 79 - "Community 79"
Cohesion: 0.23
Nodes (13): fetch_by_slug(), _fetch_slug(), find_shortterm(), main(), data/shortterm.py — Kisa vadeli BTC/ETH Up/Down market bulucu. Slug'i o anki UTC, Tek slug için bağımsız sorgu — main_loop._monitor_positions kullanır., Su an ve son birkac periyodun slug'larini uretir., Su an ve son birkac periyodun slug'larini uretir. (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (12): _parse(), tests/test_shortterm.py — data/shortterm.py testleri. parse_market_window unit t, slugs_for_now her interval için btc/eth/sol/xrp içermeli., fetch_by_slug(slug) — session parametresi olmadan çağrılabilmeli (main_loop kull, 4 asset × 3 interval × 7 lookback = 84 slug — 80+ hedefine ulaşmış olmalı., test_fetch_by_slug_takes_single_arg(), test_parse_invalid(), test_parse_json_string() (+4 more)

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
Cohesion: 0.29
Nodes (5): log_candidate(), bool, str, db/logger.py — Aday ve pozisyon kayıtları. conn=None → sessiz atla., db/schema.py — SQLite şeması ve başlatma.

### Community 86 - "Community 86"
Cohesion: 0.22
Nodes (9): Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,     aynı turd, BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır., test_bankroll_reads_from_env() (+1 more)

### Community 87 - "Community 87"
Cohesion: 0.11
Nodes (21): _monitor_positions(), Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., Açık pozisyonları izler, çıkış koşulu varsa kapatır., _open_position() (+13 more)

### Community 88 - "Community 88"
Cohesion: 0.24
Nodes (11): arm(), disarm(), monitor/kill_switch.py — Dosya tabanlı kill switch. touch logs/KILL → durur., hard_resume(), monitor/state.py — Paylasilan bot durumu: main_loop ve telegram_commands arasin, soft_resume(), handle_command(), _query_daily_pnl() (+3 more)

### Community 89 - "Community 89"
Cohesion: 0.18
Nodes (11): build_durum_message(), is_authorized(), bool, float, str, /durum acik pozisyon yoksa bos mesaj vermemeli, /durum mesaji acik pozisyon sayisi icermeli, /durum acik pozisyon yoksa bos mesaj vermemeli (+3 more)

### Community 90 - "Community 90"
Cohesion: 0.33
Nodes (6): load_closed_today(), Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., load_closed_today yalnızca bugünün UTC kapanışlarını döndürür, önceki günleri de, test_load_closed_today_returns_only_todays()

### Community 91 - "Community 91"
Cohesion: 0.33
Nodes (5): Değişen Dosyalar, Heal Notification + İstatistik Berabere Fix Implementation Plan, Task 1: notify_resolved_late fonksiyonu, Task 2: _heal_pending_resolutions notify çağrısı, Task 3: /istatistik berabere fix

### Community 92 - "Community 92"
Cohesion: 0.20
Nodes (10): parse_hours(), /istatistik6' → 6  |  '/istatistik' → None, /istatistik6' → 6  |  '/istatistik' → None, /istatistik → None (tum zamanlar), /istatistikABC → None (sayisal degil), test_parse_hours_12_returns_12(), test_parse_hours_24_returns_24(), test_parse_hours_6_returns_6() (+2 more)

### Community 94 - "Community 94"
Cohesion: 0.40
Nodes (5): fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., test_heal_skips_when_api_still_none()

### Community 95 - "Community 95"
Cohesion: 0.50
Nodes (4): endDate yoksa None döner., bestAsk yoksa None döner., test_parse_market_window_missing_best_ask_returns_none(), test_parse_market_window_missing_end_date_returns_none()

### Community 96 - "Community 96"
Cohesion: 0.50
Nodes (4): Gelecekteki bir market için seconds_remaining > 0., Geçmişteki bir market için seconds_remaining < 0., test_parse_market_window_seconds_remaining_future(), test_parse_market_window_seconds_remaining_past()

### Community 97 - "Community 97"
Cohesion: 0.67
Nodes (3): /baslat SOFT_PAUSED'u temizler., /baslat SOFT_PAUSED'u temizler., test_baslat_clears_soft_paused()

### Community 98 - "Community 98"
Cohesion: 0.67
Nodes (3): /hardbaslat HARD_PAUSED'u temizler., /hardbaslat HARD_PAUSED'u temizler., test_hardbaslat_clears_hard_paused()

## Knowledge Gaps
- **274 isolated node(s):** `str`, `int`, `PreToolUse`, `allow`, `bool` (+269 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `scan_edges()` connect `Community 18` to `Community 1`, `Community 6`, `Community 7`, `Community 8`, `Community 14`, `Community 23`, `Community 33`, `Community 65`, `Community 66`, `Community 67`, `Community 68`, `Community 69`, `Community 70`, `Community 71`, `Community 72`, `Community 73`, `Community 74`, `Community 75`, `Community 76`, `Community 77`, `Community 79`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `fair_yes()` connect `Community 5` to `Community 9`, `Community 18`, `Community 7`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `poll_commands()` connect `Community 23` to `Community 88`, `Community 89`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **What connects `main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü.`, `DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir.`, `DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru` to the rest of the system?**
  _633 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.13071895424836602 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.047619047619047616 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.07142857142857142 - nodes in this community are weakly interconnected._