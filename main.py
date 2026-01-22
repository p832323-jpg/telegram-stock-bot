import pandas as pd
import yfinance as yf
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = "
8409526358:AAFeZEEjxaaGYMoScr1urjZPBQurBIZFXxs"

def start(update, context):
    update.message.reply_text(
        "📊 Stock Bot Ready\n\n"
        "Upload CSV file\n"
        "Column name must be: Symbol\n"
        "Example:\nTCS.NS\nINFY.NS"
    )

def analyze(symbol):
    df = yf.Ticker(symbol).history(period="3mo")
    if df.empty:
        return f"{symbol} ❌ No data"

    close = df["Close"]
    rsi = 100 - (100 / (1 + close.diff().clip(lower=0).rolling(14).mean() /
                       (-close.diff().clip(upper=0).rolling(14).mean())))

    rsi_val = round(rsi.iloc[-1], 2)
    price = round(close.iloc[-1], 2)

    if rsi_val < 30:
        action = "✅ BUY"
    elif rsi_val > 70:
        action = "❌ SELL"
    else:
        action = "⏸ HOLD"

    return f"{symbol}\n💰 Price: {price}\n📈 RSI: {rsi_val}\n👉 {action}"

def handle_csv(update, context):
    file = update.message.document.get_file()
    file.download("stocks.csv")

    df = pd.read_csv("stocks.csv")
    replies = []

    for s in df["Symbol"]:
        replies.append(analyze(s))

    update.message.reply_text("\n\n".join(replies))

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.document.mime_type("text/csv"), handle_csv))

updater.start_polling()
updater.idle()
