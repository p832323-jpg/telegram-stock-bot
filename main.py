import os
import pandas as pd
import yfinance as yf
import asyncio
import datetime as dt

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
UPDATE_INTERVAL = 1800  # 30 mins

POSSIBLE_COLUMNS = [
    "SYMBOL", "Symbol", "Instrument",
    "Security", "Stock", "Company", "Name"
]

STOCKS = []
CHAT_ID = None


# ---------------- HELPERS ----------------

def market_open():
    now = dt.datetime.now().time()
    return dt.time(9, 15) <= now <= dt.time(15, 30)


def clean_symbol(name):
    name = str(name).upper()
    name = name.replace(" LTD", "").replace(" LIMITED", "")
    name = name.replace("&", "").replace(" ", "")
    return name + ".NS"


def detect_table(df):
    for i in range(len(df)):
        row = df.iloc[i].astype(str).str.upper().tolist()
        for col in POSSIBLE_COLUMNS:
            if col in row:
                df.columns = df.iloc[i]
                return df[i + 1:]
    return None


def extract_symbols(df):
    for c in df.columns:
        if str(c).upper() in [x.upper() for x in POSSIBLE_COLUMNS]:
            return list(set(clean_symbol(x) for x in df[c].dropna()))
    return []


def analyse(symbol):
    try:
        data = yf.download(symbol, period="5d", interval="15m", progress=False)
        if data.empty:
            return "NO DATA"

        close = data["Close"]
        price = close.iloc[-1]
        sma = close.rolling(10).mean().iloc[-1]

        return "SELL 🔴" if price < sma else "HOLD 🟢"
    except:
        return "ERROR"


# ---------------- TELEGRAM ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "👋 Hi bro!\n\n"
        "📂 CSV / Excel upload pannunga\n"
        "⏱ Market open → 30 mins update\n"
        "📊 SELL / HOLD analysis"
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOCKS, CHAT_ID
    CHAT_ID = update.effective_chat.id

    doc = update.message.document
    file = await doc.get_file()
    path = doc.file_name
    await file.download_to_drive(path)

    try:
        raw = pd.read_csv(path, header=None) if path.endswith(".csv") else pd.read_excel(path, header=None)
        df = detect_table(raw)

        if df is None:
            await update.message.reply_text("❌ Stock table kandupidikka mudiyala.")
            return

        STOCKS = extract_symbols(df)

        if not STOCKS:
            await update.message.reply_text("❌ Stock names illa.")
            return

        await update.message.reply_text(
            f"✅ {len(STOCKS)} stocks loaded\n"
            "⏱ Market open → auto update start"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(path):
            os.remove(path)


# ---------------- SCHEDULER ----------------

async def market_scheduler(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID or not STOCKS or not market_open():
        return

    msg = "⏰ *30 Min Market Update*\n\n"
    for s in STOCKS:
        msg += f"{s} → {analyse(s)}\n"

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=msg,
        parse_mode="Markdown"
    )


# ---------------- MAIN ----------------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    # 🔥 CORRECT WAY (NO asyncio crash)
    app.job_queue.run_repeating(
        market_scheduler,
        interval=UPDATE_INTERVAL,
        first=UPDATE_INTERVAL
    )

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
