import os
import pandas as pd
import yfinance as yf

from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# ✅ TOKEN FROM RAILWAY VARIABLE
TOKEN = os.getenv("TELEGRAM_TOKEN")

# ---------- RSI ----------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ---------- STOCK ANALYSIS ----------
def analyze_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="3mo")

        if df.empty or len(df) < 20:
            return f"❌ {symbol}\nNot enough data"

        close = df["Close"]
        price = round(close.iloc[-1], 2)
        rsi = round(calculate_rsi(close).iloc[-1], 2)

        ema10 = close.ewm(span=10).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        trend = "📈 Uptrend" if ema10 > ema50 else "📉 Downtrend"

        if rsi < 30:
            action = "✅ BUY"
            hold = "1–3 Months"
        elif rsi > 70:
            action = "❌ SELL IMMEDIATELY"
            hold = "EXIT"
        else:
            action = "⏸ HOLD"
            hold = "WAIT"

        return f"""
📊 {symbol}

💰 Price: {price}
📉 RSI: {rsi}
📊 Trend: {trend}

👉 Action: {action}
⏳ Hold: {hold}
"""
    except Exception as e:
        return f"❌ Error analyzing {symbol}"

# ---------- START ----------
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Welcome to Stock AI Bot\n\n"
        "📂 Send a CSV file\n"
        "🧾 Column name must be: Symbol\n"
        "📌 Example:\nTCS.NS\nINFY.NS\nRELIANCE.NS"
    )

# ---------- CSV HANDLER ----------
def handle_csv(update: Update, context: CallbackContext):
    file = update.message.document

    if not file.file_name.endswith(".csv"):
        update.message.reply_text("❌ Please upload a CSV file")
        return

    csv_file = file.get_file()
    path = "stocks.csv"
    csv_file.download(path)

    df = pd.read_csv(path)

    if "Symbol" not in df.columns:
        update.message.reply_text("❌ CSV must have 'Symbol' column")
        return

    update.message.reply_text("🔍 Analyzing stocks...")

    for symbol in df["Symbol"]:
        result = analyze_stock(str(symbol).strip())
        update.message.reply_text(result)

# ---------- MAIN ----------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/csv"), handle_csv))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
