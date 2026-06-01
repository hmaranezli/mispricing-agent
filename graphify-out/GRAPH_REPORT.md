# Graph Report - mispricing_agent  (2026-06-01)

## Corpus Check
- 64 files · ~41,028 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 829 nodes · 1321 edges · 54 communities (51 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `50abe683`
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
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]

## God Nodes (most connected - your core abstractions)
1. `scan_edges()` - 36 edges
2. `verify()` - 30 edges
3. `fair_yes()` - 25 edges
4. `risk()` - 24 edges
5. `redteam()` - 22 edges
6. `current_price()` - 18 edges
7. `parse_market_window()` - 18 edges
8. `execute()` - 17 edges
9. `_monitor_positions()` - 16 edges
10. `check_exit()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_scan_edges_returns_list()` --calls--> `scan_edges()`  [EXTRACTED]
  tests/test_scout.py → council/scout.py
- `test_load_open_positions_returns_open_ones()` --calls--> `_load_open_positions()`  [EXTRACTED]
  tests/test_main_loop.py → main_loop.py
- `test_daily_loss_includes_recovered_closed_positions()` --calls--> `_daily_loss_usd()`  [EXTRACTED]
  tests/test_main_loop.py → main_loop.py
- `_run_council()` --calls--> `gate()`  [EXTRACTED]
  main_loop.py → council/gate.py
- `_run_council()` --calls--> `redteam()`  [EXTRACTED]
  main_loop.py → council/redteam.py

## Communities (54 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (47): _asset_of(), _edge_signal(), float, str, fair: fair_yes değeri [0,1]     best_ask: YES almak için ödeyeceğimiz fiyat, tests/test_scout.py — council/scout.py testleri. Unit testler (_asset_of, _edge_, Her bulgu zorunlu alanları içeriyor., Dönen tüm bulgular MIN_EDGE_PCT eşiği üstünde. (+39 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (34): bool, bool, float, str, _result(), _fake_finding(), council/verifier.py testleri. Gerçek API kullanılır — mock yok., Scout cur_price=1.0 (imkansız) iken HL taze fiyat ~73k → drift devasa → api_mism (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (36): fair_yes(), float, str, data/fair_value.py — Binary option fair value hesaplayıcı. Model: log-normal GBM, P(asset_price > p_ref at resolution | current_price = p_now)      Args:, tests/test_fair_value.py — data/fair_value.py unit testleri Gerçek API çağrısı y, Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var ve pozitif., ETH daha yüksek vol kullandığı için aynı sapmayla daha geniş dağılım. (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (29): current_price(), fetch_candles(), fetch_candles_range(), main(), price_at_timestamp(), float, int, str (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (54): main(), _process_market(), council/scout.py — KATMAN 1: Keşif Ajanı.  Edge tanımı (matematiksel):   fair_ye, Tek marketi değerlendirir. Edge yoksa veya veri eksikse None., _fetch_slug(), find_shortterm(), main(), _parse() (+46 more)

### Community 5 - "Community 5"
Cohesion: 0.43
Nodes (6): fetch_market_state(), main(), _post(), data/hyperliquid.py — Hyperliquid veri katmani (public, key gerekmez). BTC/ETH i, Basit yon gostergesi: mark vs oracle + gunluk degisim + funding., _signal()

### Community 6 - "Community 6"
Cohesion: 0.53
Nodes (5): fetch_crypto_markets(), _fmt(), main(), _parse(), data/polymarket.py — Polymarket veri katmani (ADIM 1: canli fiyat cekme) Gamma A

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (23): 1. Sormadan değişiklik yok, 2. DRY_RUN varsayılan, 3. Verisiz/uydurma işlem yok (anti-hallucination), 4. Konsey onayı zorunlu, 5 katmanlı konsey (sırayla inşa edilecek), 5. Risk limitleri kutsaldır, 6. Test-önce (TDD), 7. Her şey loglanır (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (70): main(), council/gate.py — KATMAN 5: Kapı.  Son karar ve uygulama katmanı. 4 katmandan ge, Manuel test: Scout→Verifier→RedTeam→Risk→Gate tam zinciri., _fee_adjusted_edge(), main(), _parse_taker_fee(), bool, float (+62 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (17): load_closed_today(), Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery., _load_open_positions(), main(), main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü., DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru, check(), bool (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (35): check_exit(), close_position(), _log(), float, int, Path, str, position/manager.py — Açık pozisyon takibi ve çıkış kararı. (+27 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (34): execute(), _log(), Path, str, execution/executor.py — DRY_RUN order logger., Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür., _finding(), _gate() (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (33): init_schema(), db/schema.py — SQLite şeması ve başlatma., conn(), tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu., positions tablosu ref_price ve edge sütunlarına sahip olmalı., log_position_open ref_price ve edge değerlerini DB'ye yazar., positions tablosu realized_pnl sütununa sahip olmalı., Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.     entry=0.40, exit=0 (+25 more)

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (27): _kelly(), bool, float, int, str, Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0., Pozisyon boyutlandırması ve sistem limiti kontrolü.      Args:         finding:, _result() (+19 more)

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (24): _confidence_score(), gate(), _gate_decide(), _log(), float, 0-100 güven skoru. 4 bileşen ağırlıklı toplam., Güven skoru hesapla, CONFIDENCE_THRESHOLD kontrolü yap., Kararı LOG_FILE'a yaz. Dizin yoksa oluşturur. (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (23): tests/test_monitor.py — monitor/ birim testleri. Sıfır gerçek HTTP/dosya., pm_exit_price yoksa P&L satırı olmaz., logs/KILL dosyası varsa check() True döner., logs/KILL dosyası yoksa check() False döner., Token + chat_id varsa requests.post çağrılır., Token yoksa requests.post hiç çağrılmaz., DRY_RUN=True iken mesaj '[DRY RUN]' ile başlar., notify_open mesajı asset ve action içerir. (+15 more)

### Community 23 - "Community 23"
Cohesion: 0.11
Nodes (17): 1. Günlük Kayıp Limiti (HALT), 2. Açık Pozisyon Limiti, 3. Edge Geçerlilik Kontrolü (çift emniyet), 4. Kelly Hesabı ve Minimum Pozisyon, 5. İnsan Onayı Bayrağı (VETO DEĞİL), Amaç, Bağımlılıklar, Dosya Yapısı (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): Akış, Amaç, Bağımlılıklar, Dosya Yapısı, Gelecek: DB Entegrasyonu, Güven Skoru Formülü, Input / Output, Kalibrasyon (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (12): Dosya Yapısı, Doğrulama, Risk Katmanı (Katman 4) Implementation Plan, Sabit Referanslar (config.py'den, değiştirme), Task 1: Skeleton + Output Şeması Testi, Task 2: `_kelly()` — YES ve NO Kolları, Task 3: Günlük Kayıp Limiti (Halt), Task 4: Açık Pozisyon Limiti (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (11): 10. Bağımlılıklar, 1. Amaç, 2. Arayüz, 3. Finding Yapısı (scout çıktısı — referans), 4. Guard Sırası, 5. Giriş Fiyatı Hesabı, 6. Pozisyon Kaydı (dönüş değeri), 7. JSONL Log (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (10): 1. `data/shortterm.py` — `fetch_resolved(slug)`, 2. `main_loop._monitor_positions` güncelleme, 3. P&L hesabı, 4. `monitor/notifier.notify_close` güncelleme, API Kanıtı, Değişmeyen Şeyler, P&L Resolution Design, Problem (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (8): Dosya Haritası, Matematiksel temel, Scout Fair Value Rewrite — Implementation Plan, Sıradaki Aşama (Bu Plandan Sonra), Task A1: data/fair_value.py — Binary Option Fair Value Modeli, Task A3: data/shortterm.py — parse_market_window() ekle, Task B1: council/scout.py — Tam Rewrite (Fair Value Modeli), Verification Checklist (Tamamlama Öncesi)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (9): 6 Kontrol, Amaç, Dosya Değişiklikleri, Eşik Sabitleri (redteam.py içinde), Fee Hesabı, RedTeam (Katman 3) — Tasarım Dokümanı, Sorumluluk Sınırı, Test Stratejisi (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (9): Amaç, Dosya Değişiklikleri, Doğrulama Akışı, İki Başarısızlık Türü, Output Formatı, Re-fetch Edilenler, Test Stratejisi, Tolerans Eşikleri (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (8): Dosya Yapısı, Doğrulama, Gate Katmanı (Katman 5) Implementation Plan, Sabit Referanslar (config.py'den, değiştirme), Task 1: Skeleton + `_confidence_score()` + 4 Test, Task 2: `_gate_decide()` + 3 Test, Task 3: `_log()` + `gate()` + 3 Async Test, Task 4: `main()` + Tam Test Koşusu

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (7): Dosya Haritası, Fonksiyon İmzaları (referans), main_loop Implementation Plan, Self-Review, Task 1: `main_loop.py` iskeleti + `_run_council()`, Task 2: `_scan_and_execute()`, Task 3: `_monitor_positions()`

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (7): Dosya Haritası, position/ Implementation Plan, Referans: Test Sabitleri, Self-Review, Task 1: `_log()` + `close_position()`, Task 2: `check_exit()` — zaman ve expiry kontrolleri, Task 3: `check_exit()` — thesis ve kâr hedefi

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (7): Dosya Haritası, Realized P&L + Daily Loss Restart Recovery Implementation Plan, Task 1: Schema Migration — `realized_pnl` Kolonu, Task 2: `log_position_close` — P&L Hesapla ve Yaz, Task 3: `load_closed_today` — Restart Recovery Sorgusu, Task 4: Main Loop Startup Recovery, Task 5: Tam Suite + Bot Restart

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (6): Dosya Haritası, execution/ Implementation Plan, Self-Review Notları, Task 1: `_log()` yardımcı fonksiyon, Task 2: Guard — gate fail ve max pozisyon, Task 3: execute() happy path — pozisyon kaydı

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (6): Dosya Haritası, P&L Resolution Implementation Plan, Task 1: `_parse_resolution` + `fetch_resolved` — shortterm.py, Task 2: `_monitor_positions` güncelleme, Task 3: `notify_close` P&L satırı, Task 4: Tam suite + bot restart

### Community 37 - "Community 37"
Cohesion: 0.33
Nodes (5): Dosya Haritası, monitor/ Implementation Plan, Task 1: monitor/notifier.py — 6 test, Task 2: monitor/kill_switch.py — 2 test, Task 3: main_loop.py entegrasyonu — mevcut 6 test kırılmaz

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (5): Dosya Haritası, Task 1: Scout'a slug ekle, Task 2: council/verifier.py — Bağımsız Doğrulayıcı, Verification Checklist (Tamamlama Öncesi), Verifier (Katman 2) Implementation Plan

### Community 39 - "Community 39"
Cohesion: 0.40
Nodes (4): Dosya Haritası, RedTeam (Katman 3) Implementation Plan, Task 1: council/redteam.py — Şeytan Avukatı, Verification Checklist

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (15): 1. Problem, 2. Root Cause, 3. Yaklaşım — DB-driven Healing, 4. Dosya Haritası, 5. Arayüzler, 6. exit_reason Sözleşmesi, 7. P&L Formülü (değişmiyor), 8. Test Planı (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.23
Nodes (15): _finding(), _pass_gate(), _pass_redteam(), _pass_risk(), _pass_verify(), tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı., Aynı slug için açık pozisyon varsa _run_council çağrılmaz., verify() fail → _run_council None döner. (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (13): backfill(), fetch_resolved(), str, Kapanmış market için resolution fiyatlarını döndürür.      Returns: {"yes_exit":, get_connection(), log_candidate(), patch_position_resolution(), bool (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.14
Nodes (13): 1. Genel Bakış, 2. Exit Reason Dağılımı, 3. Asset Bazında Performans, 4. Konsey Veto Dağılımı, 5. En İyi / En Kötü 3 Trade, Amaç, Dosya Yapısı, Kapsam Dışı (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.41
Nodes (11): _by_asset(), _by_exit_reason(), main(), _overview(), _pct(), int, str, run() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.21
Nodes (12): _monitor_positions(), Açık pozisyonları izler, çıkış koşulu varsa kapatır., _open_position(), Açık pozisyon fixture'ı., check_exit sinyal verince pozisyon open'dan closed'a geçer., parse_market_window None + fetch_resolved None → market_expired ile kapatılır., window=None iken fetch_resolved sonuç verirse pm_exit_price dolu kapanır (YES)., NO pozisyon erken çıkışta pm_exit_price = 1 - YES_ask (NO bid fiyatı, YES ask de (+4 more)

### Community 47 - "Community 47"
Cohesion: 0.28
Nodes (9): float, _daily_loss_usd(), Yeni fırsatları tarar, konsey geçenleri açar., Bugün kapanan pozisyonlardan gerçekleşen kaybı toplar., Finding'i 5 katmandan geçirir. Herhangi biri düşerse None., _run_council(), _scan_and_execute(), MAX_OPEN_POSITIONS doluysa scan_edges hiç çağrılmaz. (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (9): int, _heal_pending_resolutions(), market_expired + pm_exit_price=None kayıtları için resolution retry eder., fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır., fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz., limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır., test_heal_fixes_null_pnl_when_api_returns(), test_heal_respects_limit() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (7): log_position_close(), log_position_open(), DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır., DRY_RUN=True → _run_council'a daily_loss_usd=0 geçilir, kayıp limiti uygulanmaz., Restart sonrası DB'den yüklenen bugünün kapanan pozisyonları _daily_loss_usd'e d, test_daily_loss_includes_recovered_closed_positions(), test_load_open_positions_returns_open_ones()

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (6): Dosya Haritası, market_expired Heal — Implementation Plan, Task 1: `patch_position_resolution()` — DB Patch Fonksiyonu, Task 2: Retroaktif Backfill Script, Task 3: `_heal_pending_resolutions()` — Yapısal Fix, Task 4: Verification — Strateji Analizine Hazırlık

### Community 51 - "Community 51"
Cohesion: 0.40
Nodes (4): Dosya Haritası, Performance Analysis Script Implementation Plan, Self-Review Notu, Task 1: `analysis/` dizini ve `performance.py`

## Knowledge Gaps
- **193 isolated node(s):** `str`, `int`, `PreToolUse`, `allow`, `str` (+188 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `scan_edges()` connect `Community 15` to `Community 0`, `Community 1`, `Community 4`, `Community 47`, `Community 16`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `verify()` connect `Community 15` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 47`, `Community 16`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `fair_yes()` connect `Community 2` to `Community 17`, `Community 4`, `Community 15`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **What connects `main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü.`, `DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri dolduru`, `Bugün kapanan pozisyonlardan gerçekleşen kaybı toplar.` to the rest of the system?**
  _411 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0549645390070922 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06756756756756757 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.07396870554765292 - nodes in this community are weakly interconnected._