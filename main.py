import os
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

UPDATE_INTERVAL = 30 * 60  # 30 minutes

POSSIBLE_COLUMNS = [
    "SYMBOL", "Symbol", "Stock", "Stock Name", "Security",
    "Company", "Instrument", "Name"
]

user_stocks = {}  # chat_id -> list of symbols


# ---------- BASIC COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi Bro!\n\n"
        "📂 Groww Excel / CSV file upload pannunga\n"
        "❌ Manual edit thevai illa\n"
        "⏱ Market open to close – every 30 mins\n"
        "🤖 SELL / HOLD auto analyse pannuven"
    )


# ---------- HELPERS ----------
def detect_stock_column(df: pd.DataFrame):
    for col in df.columns:
        if str(col).strip().upper() in [c.upper() for c in POSSIBLE_COLUMNS]:
            return col
    return None


def clean_symbol(name: str):
    name = str(name).upper()
    for x in [" LTD", " LIMITED", " PVT", " PVT LTD"]:
        name = name.replace(x, "")
    name = name.replace(" ", "")
    return name + ".NS"


def analyse_stock(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="5d", interval="30m")
        if data.empty:
            return "❓ NO DATA"

        close = data["Close"]
        last = close.iloc[-1]
        avg = close.mean()

        if last > avg:
            return "🟢 HOLD"
        else:
            return "🔴 SELL / WATCH"
    except:
        return "⚠️ ERROR"


# ---------- FILE HANDLER ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    file = await update.message.document.get_file()
    filename = update.message.document.file_name.lower()
    path = f"/tmp/{filename}"
    await file.download_to_drive(path)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except Exception:
        await update.message.reply_text("❌ File read panna mudiyala.")
        return

    stock_col = detect_stock_column(df)
    if not stock_col:
        await update.message.reply_text(
            f"❌ Stock column kandupidikka mudiyala.\n\nFound columns:\n{list(df.columns)}"
        )
        return

    symbols = [
        clean_symbol(x)
        for x in df[stock_col].dropna().unique().tolist()
    ]

    if not symbols:
        await update.message.reply_text("❌ Stock symbols empty.")
        return

    user_stocks[chat_id] = symbols

    await update.message.reply_text(
        f"✅ {len(symbols)} stocks detected.\n"
        "⏱ Every 30 mins update start aagiduchu 🔥"
    )

    await send_analysis(chat_id, context)


# ---------- SEND ANALYSIS ----------
async def send_analysis(chat_id, context: ContextTypes.DEFAULT_TYPE):
    symbols = user_stocks.get(chat_id)
    if not symbols:
        return

    msg = "📊 *Portfolio Update*\n\n"

    for sym in symbols:
        result = analyse_stock(sym)
        msg += f"{sym} : {result}\n"

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown"
    )


# ---------- SCHEDULER ----------
async def market_scheduler(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in user_stocks.keys():
        await send_analysis(chat_id, context)


# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    if app.job_queue:
        app.job_queue.run_repeating(
            market_scheduler,
            interval=UPDATE_INTERVAL,
            first=UPDATE_INTERVAL
        )

    print("🤖 Stock AI Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
