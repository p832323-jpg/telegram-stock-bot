import os
import re
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
UPDATE_INTERVAL = 30 * 60  # 30 mins

user_stocks = {}

# -------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi Bro!\n\n"
        "📂 Groww Excel / CSV upload pannunga\n"
        "❌ Manual edit vendam\n"
        "⏱ Every 30 mins SELL / HOLD update varum"
    )

# -------- HELPERS ----------
def is_valid_stock(name: str) -> bool:
    name = name.upper().strip()

    # remove unwanted words
    blacklist = [
        "TOTAL", "SUMMARY", "VALUE", "P&L", "CHARGES",
        "BROKERAGE", "GST", "STT", "DUTY",
        "UNREALISED", "REALISED", "STATEMENT",
        "FROM", "TO", "AS ON", "CLIENT"
    ]

    if any(word in name for word in blacklist):
        return False

    # only alphabets & length check
    if not re.fullmatch(r"[A-Z]{3,20}", name):
        return False

    return True


def clean_symbol(name: str):
    return name.upper().strip() + ".NS"


def analyse_stock(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="5d", interval="30m")
        if data.empty:
            return "❓ NO DATA"

        close = data["Close"]
        if close.iloc[-1] > close.mean():
            return "🟢 HOLD"
        else:
            return "🔴 SELL / WATCH"
    except:
        return "⚠️ ERROR"


# -------- FILE HANDLER ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    file = await update.message.document.get_file()
    name = update.message.document.file_name.lower()
    path = f"/tmp/{name}"
    await file.download_to_drive(path)

    try:
        if name.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except:
        await update.message.reply_text("❌ File read panna mudiyala.")
        return

    found = set()

    for col in df.columns:
        for val in df[col].dropna().astype(str):
            val = val.upper().strip()
            if is_valid_stock(val):
                found.add(clean_symbol(val))

    if not found:
        await update.message.reply_text("❌ Valid stock names kandupidikka mudiyala.")
        return

    user_stocks[chat_id] = list(found)

    await update.message.reply_text(
        f"✅ {len(found)} REAL stocks detected\n"
        "🔥 Every 30 mins update start aagiduchu"
    )

    await send_analysis(chat_id, context)


# -------- ANALYSIS ----------
async def send_analysis(chat_id, context):
    stocks = user_stocks.get(chat_id)
    if not stocks:
        return

    msg = "📊 *Portfolio Update*\n\n"
    for s in stocks:
        msg += f"{s} : {analyse_stock(s)}\n"

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown"
    )


# -------- SCHEDULER ----------
async def scheduler(context):
    for cid in user_stocks:
        await send_analysis(cid, context)


# -------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    if app.job_queue:
        app.job_queue.run_repeating(
            scheduler,
            interval=UPDATE_INTERVAL,
            first=UPDATE_INTERVAL
        )

    print("🤖 Stock AI Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
