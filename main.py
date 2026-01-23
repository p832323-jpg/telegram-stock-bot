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
UPDATE_INTERVAL = 30 * 60  # 30 minutes

user_stocks = {}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi Bro!\n\n"
        "📂 Groww Excel / CSV upload pannunga\n"
        "❌ Manual edit vendam\n"
        "⏱ Every 30 mins SELL / HOLD update varum"
    )

# ---------------- HELPERS ----------------
def clean_symbol(name: str):
    return name.upper().strip().replace(" ", "") + ".NS"


def is_real_stock(name: str) -> bool:
    name = name.upper().strip()

    # must be single word alphabets
    if not re.fullmatch(r"[A-Z]{3,20}", name):
        return False

    # blacklist
    blacklist = [
        "ISIN", "QUANTITY", "TOTAL", "SUMMARY", "VALUE",
        "P&L", "CHARGES", "BROKERAGE", "GST", "STT",
        "REALISED", "UNREALISED", "STATEMENT"
    ]

    if name in blacklist:
        return False

    return True


def analyse_stock(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="5d", interval="30m")
        if data.empty:
            return "❓ NO DATA"

        close = data["Close"]
        return "🟢 HOLD" if close.iloc[-1] > close.mean() else "🔴 SELL / WATCH"
    except:
        return "⚠️ ERROR"


# ---------------- FILE HANDLER ----------------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    file = await update.message.document.get_file()
    fname = update.message.document.file_name.lower()
    path = f"/tmp/{fname}"
    await file.download_to_drive(path)

    try:
        df = pd.read_csv(path) if fname.endswith(".csv") else pd.read_excel(path)
    except:
        await update.message.reply_text("❌ File read panna mudiyala.")
        return

    # find stock column ONLY
    stock_col = None
    for col in df.columns:
        if str(col).lower() in ["stock name", "company", "instrument", "security"]:
            stock_col = col
            break

    if not stock_col:
        await update.message.reply_text("❌ Stock Name column kandupidikka mudiyala.")
        return

    stocks = []
    for val in df[stock_col].dropna():
        name = str(val).upper().strip()
        if is_real_stock(name):
            stocks.append(clean_symbol(name))

    if not stocks:
        await update.message.reply_text("❌ Valid NSE stocks illa.")
        return

    user_stocks[chat_id] = list(set(stocks))

    await update.message.reply_text(
        f"✅ {len(user_stocks[chat_id])} REAL stocks detected\n"
        "🔥 Every 30 mins update start aagiduchu"
    )

    await send_analysis(chat_id, context)


# ---------------- ANALYSIS ----------------
async def send_analysis(chat_id, context):
    stocks = user_stocks.get(chat_id)
    if not stocks:
        return

    msg = "📊 *Portfolio Update*\n\n"
    for s in stocks:
        msg += f"{s} : {analyse_stock(s)}\n"

    await context.bot.send_message(chat_id, msg, parse_mode="Markdown")


# ---------------- SCHEDULER ----------------
async def scheduler(context):
    for cid in user_stocks:
        await send_analysis(cid, context)


# ---------------- MAIN ----------------
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

    print("🤖 Stock AI Bot Running")
    app.run_polling()


if __name__ == "__main__":
    main()
