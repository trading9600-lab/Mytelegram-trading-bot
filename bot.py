import os
import time
import requests
import pandas as pd
from datetime import datetime

# =========================
# ENV VARIABLES (Railway)
# =========================
BOT_TOKEN = os.getenv("8364584748:AAFeym3et4zJwmdKRxYtP3ieIKV8FuPWdQ8")
CHAT_ID = os.getenv("@Tradecocom")

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.binance.us/api/v3/klines"

PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

STATE_FILE = "last_signal.txt"
SLEEP_TIME = 300  # 5 minutes


# =========================
# TELEGRAM
# =========================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload, timeout=10)


# =========================
# BINANCE DATA
# =========================
def fetch_klines(symbol, interval, limit=100):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    r = requests.get(BASE_URL, params=params, timeout=10)
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# =========================
# DUPLICATE CONTROL
# =========================
def load_last_signal():
    if not os.path.exists(STATE_FILE):
        return ""
    return open(STATE_FILE).read().strip()


def save_last_signal(signal):
    with open(STATE_FILE, "w") as f:
        f.write(signal)


# =========================
# SIGNAL LOGIC
# =========================
def check_signals():
    last_signal = load_last_signal()

    for pair in PAIRS:
        for tf_name, tf in TIMEFRAMES.items():

            df = fetch_klines(pair, tf)

            df["ema20"] = ema(df["close"], 20)
            df["ema50"] = ema(df["close"], 50)

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            signal = None

            # EMA CROSS
            if prev.ema20 < prev.ema50 and curr.ema20 > curr.ema50:
                signal = "BUY"
            elif prev.ema20 > prev.ema50 and curr.ema20 < curr.ema50:
                signal = "SELL"

            # BREAKOUT / BREAKDOWN (last 15 candles)
            recent_high = df["high"].iloc[-16:-1].max()
            recent_low = df["low"].iloc[-16:-1].min()

            if curr.close > recent_high:
                signal = "BULLISH BREAKOUT"
            elif curr.close < recent_low:
                signal = "BEARISH BREAKDOWN"

            if signal:
                signal_id = f"{pair}_{tf}_{signal}"

                if signal_id != last_signal:
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

                    message = (
                        f"🚨 TradingCo Alert\n\n"
                        f"Pair: {pair}\n"
                        f"Timeframe: {tf_name}\n"
                        f"Signal: {signal}\n"
                        f"Time: {now}"
                    )

                    send_message(message)
                    save_last_signal(signal_id)
                    return  # ONE signal per cycle only


# =========================
# 24/7 LOOP (RAILWAY)
# =========================
if __name__ == "__main__":
    send_message("✅ TradingCo bot started successfully (Railway 24/7)")
    while True:
        try:
            check_signals()
        except Exception as e:
            send_message(f"⚠️ Bot error: {e}")
        time.sleep(SLEEP_TIME)
          
