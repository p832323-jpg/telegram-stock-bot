import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yfinance as yf

TOKEN = os.getenv("BOT_TOKEN")

POSSIBLE_COLUMNS = [
    "Stock Name",
    "Instrument",
    "Company",
    "Security Name",
    "Stock",
    "Symbol"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi!\n\n"
        "📂 Groww Holdings Excel (.xlsx) file upload pannunga\n"
        "❌ Manual edit thevai illa\n"
        "🤖 Naan auto analyse panni SELL / HOLD solluven"
    )

def clean_symbol(name: str):
    name = str(name).upper()
    remove_words = [" LTD.", " LIMITED", " LTD", " LIMITED."]
    for w in remove_words:
        name = name.replace(w, "")
    name = name.replace(" ", "")
    return name + ".NS"

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "groww.xlsx"
    await file.download_to_drive(file_path)

    try:
        df = pd.read_excel(file_path)
    except Exception:
        await update.message.reply_text("❌ Excel file read panna mudiyala.")
        return

    stock_column = None
    for col in POSSIBLE_COLUMNS:
        if col in df.columns:
            stock_column = col
            break

    if stock_column is None:
        await update.message.reply_text(
            "❌ Stock column kandupidikka mudiyala.\n"
            f"Found columns:\n{list(df.columns)}"
        )
        return

    stocks = df[stock_column].dropna().tolist()
    symbols = [clean_symbol(s) for s in stocks]

    reply = "📊 *Groww Holdings – Analysis*\n\n"

    for sym in symbols:
        try:
            data = yf.Ticker(sym).history(period="5d")
            if data.empty:
                reply += f"{sym} : ❓ Data illa\n"
                continue

            close = data["Close"]
            if close.iloc[-1] > close.mean():
                reply += f"{sym} : 🟢 HOLD\n"
            else:
                reply += f"{sym} : 🔴 SELL / WATCH\n"
        except:
            reply += f"{sym} : ⚠️ Error\n"

    await update.message.reply_text(reply, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
