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
DRY_RUN              = False  # LIVE — gercek orderlar gidiyor
MAX_TRADE_PCT        = 0.05   # Tek trade max sermayenin %5'i
MAX_OPEN_POSITIONS   = 5      # Ayni anda max 5 acik pozisyon
BUST_PROTECTION_PCT  = 0.50   # Bankroll baslangicin %50'sine dusunce → HARD STOP
STREAK_WARN_COUNT    = 6      # N arka arkaya kayip → SOFT STOP (karda da zararda da)
MIN_EDGE_PCT         = 0.05   # Min %5 edge yoksa trade onerilmez
CONFIDENCE_THRESHOLD = 50     # Konsey guven skoru esigi (0-100) — 75→50 darboğaz düzeltmesi
MAX_HOLD_MINUTES     = 20     # 15m marketlerin resolve'a kadar tutulabilmesi icin (14→20, hold-to-resolution)
HUMAN_APPROVAL_USD   = 50     # Bu tutar uzeri pozisyon insan onayi ister

# ── ACIL RISK MODU ──
# Yeni live entry kill-switch. False → council/telemetri/shadow CALISIR, sadece
# gercek position open atlanır. Monitor/exit/stop logic ETKILENMEZ.
# GECICI: Epoch 3 kanama — yeni entry durduruldu (2026-06-08, insan komutu)
NEW_ENTRIES_ENABLED  = False

# ── Anti-hallucination kurallari ──
REQUIRE_FRESH_API_DATA = True  # Her sayi API'den taze cekilir, hafizadan asla
HALT_ON_API_MISMATCH   = True  # API ile ajan celisirse islem durur

# ── Izlenecek varliklar ──
TRACKED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]

# ── Geçici quarantine (NO exact pricing fix sonrası yeniden değerlendirilecek) ──
BLOCKED_COMBOS = [("ETH", "NO")]  # ETH-NO: 1W/4L WR=%20 P&L=-$1.17 (2026-06-08, 24h sample)
