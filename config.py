"""
config.py — Mispricing Agent yapilandirmasi
ANAYASA: Asagidaki guardrail sabitleri ajan tarafindan DEGISTIRILEMEZ.
Degisiklik yalnizca insan eliyle, bu dosya elle duzenlenerek yapilir.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API anahtarlari (.env'den okunur, koda asla yazilmaz) ──
ANTHROPIC_API_KEY       = os.getenv("ANTHROPIC_API_KEY")
POLYMARKET_PRIVATE_KEY  = os.getenv("POLYMARKET_PRIVATE_KEY")
POLYMARKET_API_KEY      = os.getenv("POLYMARKET_API_KEY")
HYPERLIQUID_WALLET      = os.getenv("HYPERLIQUID_WALLET")
HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY")
TELEGRAM_BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID        = os.getenv("TELEGRAM_CHAT_ID")
DATABASE_URL            = os.getenv("DATABASE_URL", "postgresql://localhost/mispricing")

# ── KILITLI GUARDRAIL KURALLARI ──
DRY_RUN              = True   # PAPER-SAFE — gercek order GONDERILMEZ, sadece loglanir
MAX_TRADE_PCT        = 0.05   # Tek trade max sermayenin %5'i
MAX_OPEN_POSITIONS   = 1      # Micro-canary anti-burst cap (E7/E8: 5→1)
BUST_PROTECTION_PCT  = 0.50   # Bankroll baslangicin %50'sine dusunce → HARD STOP
STREAK_WARN_COUNT    = 6      # N arka arkaya kayip → SOFT STOP (karda da zararda da)
DAILY_LOSS_LIMIT     = 0.35   # Gunluk NET realized kayip limiti (E7 micro-canary: 0.05*6+buffer)
MAX_TRADES_FIRST_SESSION = 6  # Ilk-seans islem-sayisi capi (E10a; STREAK_WARN_COUNT ile hizali)
MIN_EDGE_PCT         = 0.05   # Min %5 edge yoksa trade onerilmez
CONFIDENCE_THRESHOLD = 50     # Konsey guven skoru esigi (0-100) — 75→50 darboğaz düzeltmesi
MAX_HOLD_MINUTES     = 20     # 15m marketlerin resolve'a kadar tutulabilmesi icin (14→20, hold-to-resolution)
HUMAN_APPROVAL_USD   = 50     # Bu tutar uzeri pozisyon insan onayi ister

# ── ACIL RISK MODU ──
# Yeni live entry kill-switch. False → council/telemetri/shadow CALISIR, sadece
# gercek position open atlanır. Monitor/exit/stop logic ETKILENMEZ.
# GECICI: Epoch 3 kanama — yeni entry durduruldu (2026-06-08, insan komutu)
NEW_ENTRIES_ENABLED  = False

# ── COUNCIL DECISION-AUTHORITY KILL SWITCH ──
# Council/multi-agent layer (scout→verifier→redteam→risk→gate) is DETERMINISTIC Python and was
# trade-path connected (council pass → execute()). De-risk gate (FOLLOW_UP_REMOVE_OR_BYPASS):
# council decision authority is DISCONNECTED from execution authority by default. False → a council
# PASS is DIAGNOSTIC ONLY and MUST NOT reach execute()/order intent; council/telemetry/shadow still
# run. This flag does NOT bypass DRY_RUN and does NOT enable any live/paper path; execution still
# routes solely by DRY_RUN when (opt-in) enabled. Default-safe = disabled.
COUNCIL_DECISION_AUTHORITY_ENABLED = False

# Telemetry V3.1 feature flag (salt-gözlem; guardrail DEĞİL, karar mantığına dokunmaz).
# False → V3.1 alanları NULL, eski V2 davranışı. Tek-bayrak kill switch.
TELEMETRY_V31_ENABLED = True

# Orderbook data-integrity (P0). Dust/depth eşiği — top-of-book'ta işlem yapılamayacak
# kadar küçük (notional < eşik) emirler best fiyat olarak KULLANILMAZ. Bu bir VERİ-KALİTE
# eşiğidir, trading karar parametresi DEĞİL (fair/edge/threshold ile karıştırılmaz).
MIN_EXECUTABLE_NOTIONAL_USD = 5.0
WS_SNAPSHOT_MAX_AGE_S = 10.0

# Live execution tick/slippage bounds (Faz 2b). Polymarket binary fiyat aralığı + taker cap.
# Veri-kalite/risk sabitleri; out-of-bounds/cap aşımı → SESSİZ clamp YOK, intent REJECTED.
PRICE_MIN = "0.01"
PRICE_MAX = "0.99"
MAX_SLIPPAGE_CAP = "0.03"   # taker limit, quote'tan max %3 sapma (aşarsa network call YOK)

# ── Anti-hallucination kurallari ──
REQUIRE_FRESH_API_DATA = True  # Her sayi API'den taze cekilir, hafizadan asla
HALT_ON_API_MISMATCH   = True  # API ile ajan celisirse islem durur

# ── Izlenecek varliklar ──
TRACKED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]

# ── Geçici quarantine (NO exact pricing fix sonrası yeniden değerlendirilecek) ──
BLOCKED_COMBOS = [("ETH", "NO")]  # ETH-NO: 1W/4L WR=%20 P&L=-$1.17 (2026-06-08, 24h sample)
