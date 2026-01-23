import os
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

TOKEN = os.getenv("BOT_TOKEN")

user_portfolios = {}   # chat_id -> list of symbols


def clean_symbol(name: str) -> str:
    name = str(name).upper()
    name = name.replace(" LTD.", "").replace(" LTD", "").replace(" LIMITED", "")
    name = name.replace("&", "").replace(" ", "")
    return name + ".NS"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi Bro!\n\n"
        "📂 Groww *Holdings Statement* Excel (.xlsx) upload pannunga\n"
        "❌ Manual edit vendam\n"
        "⏱ Every 30 mins SELL / HOLD update varum",
        parse_mode="Markdown"
    )


def extract_stocks_from_groww_xlsx(path: str):
    raw = pd.read_excel(path, header=None)

    header_row = None
    for i in range(len(raw)):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if "stock name" in row and "quantity" in row:
            header_row = i
            break

    if header_row is None:
        return []

    df = pd.read_excel(path, header=header_row)
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "stock name" not in df.columns:
        return []

    stocks = df["stock name"].dropna().tolist()
    stocks = [s for s in stocks if isinstance(s, str) and len(s) > 2]
    return stocks


async def analyse_and_send(chat_id, context: ContextTypes.DEFAULT_TYPE):
    symbols = user_portfolios.get(chat_id, [])
    if not symbols:
        return

    msg = "📊 *Portfolio Update*\n\n"

    for sym in symbols:
        try:
            data = yf.Ticker(sym).history(period="5d")
            if data.empty:
                msg += f"{sym} : ❓ NO DATA\n"
                continue

            close = data["Close"]
            if close.iloc[-1] > close.mean():
                msg += f"{sym} : 🟢 HOLD\n"
            else:
                msg += f"{sym} : 🔴 SELL / WATCH\n"
        except:
            msg += f"{sym} : ⚠️ ERROR\n"

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc.file_name.endswith(".xlsx"):
        await update.message.reply_text("❌ Only Groww Holdings Excel (.xlsx) upload pannunga")
        return

    file = await doc.get_file()
    path = "groww.xlsx"
    await file.download_to_drive(path)

    stocks = extract_stocks_from_groww_xlsx(path)

    if not stocks:
        await update.message.reply_text("❌ Valid stocks kandupidikka mudiyala.")
        return

    symbols = [clean_symbol(s) for s in stocks]
    user_portfolios[update.effective_chat.id] = symbols

    await update.message.reply_text(
        f"✅ {len(symbols)} REAL stocks detected\n"
        f"🔥 Every 30 mins update start aagiduchu"
    )

    context.job_queue.run_repeating(
        analyse_and_send,
        interval=1800,
        first=5,
        chat_id=update.effective_chat.id
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()


if __name__ == "__main__":
    main()
