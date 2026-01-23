import os
import pandas as pd
import yfinance as yf
import asyncio
import datetime as dt

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
UPDATE_INTERVAL = 1800  # 30 minutes

POSSIBLE_COLUMNS = [
    "SYMBOL", "Symbol", "Instrument", "Security",
    "Stock", "Company", "Name"
]

STOCKS = []
CHAT_ID = None
# =========================================


# ---------- BASIC HELPERS ----------

def market_open():
    now = dt.datetime.now().time()
    return dt.time(9, 15) <= now <= dt.time(15, 30)


def clean_symbol(name):
    name = str(name).upper()
    name = name.replace(" LTD", "").replace(" LIMITED", "")
    name = name.replace("&", "").replace(" ", "")
    return name + ".NS"


def detect_table(df):
    # find header row automatically (Groww / any messy excel)
    for i in range(len(df)):
        row = df.iloc[i].astype(str).str.upper().tolist()
        for col in POSSIBLE_COLUMNS:
            if col in row:
                df.columns = df.iloc[i]
                return df[i + 1:]
    return None


def extract_symbols(df):
    stock_col = None
    for c in df.columns:
        if str(c).upper() in [x.upper() for x in POSSIBLE_COLUMNS]:
            stock_col = c
            break

    if stock_col is None:
        return []

    symbols = []
    for val in df[stock_col].dropna():
        s = str(val).strip()
        if len(s) > 1:
            symbols.append(clean_symbol(s))

    return list(set(symbols))


def analyse(symbol):
    try:
        data = yf.download(symbol, period="5d", interval="15m", progress=False)
        if data.empty:
            return "NO DATA"

        close = data["Close"]
        price = close.iloc[-1]
        sma = close.rolling(10).mean().iloc[-1]

        if price < sma:
            return "SELL 🔴"
        else:
            return "HOLD 🟢"
    except:
        return "ERROR"


# ---------- TELEGRAM ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "👋 Hi bro!\n\n"
        "📂 ANY CSV / Excel upload pannunga\n"
        "⏱ Market open → every 30 mins update\n"
        "📊 ALL stocks SELL / HOLD"
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOCKS, CHAT_ID
    CHAT_ID = update.effective_chat.id

    file = await update.message.document.get_file()
    path = update.message.document.file_name
    await file.download_to_drive(path)

    try:
        if path.endswith(".csv"):
            raw = pd.read_csv(path, header=None)
        else:
            raw = pd.read_excel(path, header=None)

        df = detect_table(raw)
        if df is None:
            await update.message.reply_text("❌ Stock table kandupidikka mudiyala.")
            return

        symbols = extract_symbols(df)
        if not symbols:
            await update.message.reply_text("❌ Stock names kandupidikka mudiyala.")
            return

        STOCKS = symbols

        await update.message.reply_text(
            f"✅ {len(STOCKS)} stocks loaded.\n"
            "⏱ Market open irundha every 30 mins update varum."
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(path):
            os.remove(path)


# ---------- 30 MIN SCHEDULER ----------

async def scheduler(app):
    while True:
        await asyncio.sleep(UPDATE_INTERVAL)

        if not CHAT_ID or not STOCKS:
            continue

        if not market_open():
            continue

        msg = "⏰ *30 Min Market Update*\n\n"
        for s in STOCKS:
            msg += f"{s} → {analyse(s)}\n"

        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=msg,
            parse_mode="Markdown"
        )


# ---------- MAIN ----------

async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN env variable set pannala")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    asyncio.create_task(scheduler(app))

    print("🤖 Bot running...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
