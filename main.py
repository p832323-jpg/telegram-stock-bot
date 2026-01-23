import os
import re
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.ext import JobQueue

TOKEN = os.getenv("BOT_TOKEN")

user_stocks = {}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi Bro!\n\n"
        "📂 Groww Excel / CSV upload pannunga\n"
        "❌ Manual edit vendam\n"
        "⏱️ Every 30 mins SELL / HOLD update varum"
    )

# ---------------- CLEAN STOCK ----------------
def clean_stock(name: str):
    name = name.upper().strip()

    if not re.fullmatch(r"[A-Z]{3,20}", name):
        return None

    blacklist = [
        "ISIN","QUANTITY","SUMMARY","TOTAL","VALUE","CHARGES",
        "BROKERAGE","GST","STT","REALISED","UNREALISED",
        "STATEMENT","HOLDINGS","PNL","REPORT"
    ]

    if name in blacklist:
        return None

    return name + ".NS"

# ---------------- READ FILE ----------------
def read_file(path, fname):
    try:
        if fname.endswith(".csv"):
            return pd.read_csv(path)
        return pd.read_excel(path)
    except:
        return None

# ---------------- DETECT STOCK COLUMN ----------------
def detect_stock_column(df):
    keywords = ["stock", "company", "security", "instrument", "symbol", "scrip", "name"]
    for col in df.columns:
        c = str(col).lower()
        if any(k in c for k in keywords):
            return col
    return None

# ---------------- ANALYSIS ----------------
async def analyse_and_send(chat_id, context):
    stocks = user_stocks.get(chat_id, [])
    if not stocks:
        return

    msg = "📊 *Portfolio Update*\n\n"

    for s in stocks:
        try:
            data = yf.Ticker(s).history(period="5d")
            if data.empty:
                msg += f"{s} : ❓ NO DATA\n"
                continue

            close = data["Close"]
            if close.iloc[-1] >= close.mean():
                msg += f"{s} : 🟢 HOLD\n"
            else:
                msg += f"{s} : 🔴 SELL / WATCH\n"
        except:
            msg += f"{s} : ⚠️ ERROR\n"

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

# ---------------- FILE HANDLER ----------------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    doc = update.message.document
    file = await doc.get_file()

    fname = doc.file_name.lower()
    path = f"/tmp/{fname}"
    await file.download_to_drive(path)

    df = read_file(path, fname)
    if df is None:
        await update.message.reply_text("❌ File read panna mudiyala.")
        return

    stock_col = detect_stock_column(df)
    if not stock_col:
        await update.message.reply_text("❌ Stock Name column kandupidikka mudiyala.")
        return

    stocks = []
    for v in df[stock_col].dropna():
        s = clean_stock(str(v))
        if s:
            stocks.append(s)

    stocks = list(set(stocks))

    if not stocks:
        await update.message.reply_text("❌ Valid stocks illa.")
        return

    user_stocks[chat_id] = stocks

    await update.message.reply_text(
        f"✅ {len(stocks)} REAL stocks detected\n"
        "🔥 Every 30 mins update start aagiduchu"
    )

    await analyse_and_send(chat_id, context)

# ---------------- JOB ----------------
async def scheduled(context):
    for chat_id in user_stocks:
        await analyse_and_send(chat_id, context)

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    jobq: JobQueue = app.job_queue
    jobq.run_repeating(scheduled, interval=1800, first=1800)

    app.run_polling()

if __name__ == "__main__":
    main()
