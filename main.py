import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yfinance as yf

TOKEN = os.getenv("TELEGRAM_TOKEN")

POSSIBLE_COLUMNS = ["SYMBOL", "Symbol", "Instrument", "Security", "Stock", "Company"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi!\n\n"
        "📂 Groww Holdings Excel (.xlsx) file upload pannunga\n"
        "❌ Manual edit thevai illa\n"
        "🤖 Auto analyse panni SELL / HOLD solluven"
    )

def detect_table(df):
    for i in range(len(df)):
        row = df.iloc[i].astype(str).str.upper().tolist()
        for col in POSSIBLE_COLUMNS:
            if col in row:
                df.columns = df.iloc[i]
                return df[i+1:]
    return None

def clean_symbol(name):
    name = str(name).upper()
    name = name.replace(" LTD", "").replace(" LIMITED", "")
    name = name.replace(" ", "")
    return name + ".NS"

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = "groww.xlsx"
    await file.download_to_drive(path)

    try:
        raw = pd.read_excel(path, header=None)
    except Exception:
        await update.message.reply_text("❌ Excel read panna mudiyala.")
        return

    df = detect_table(raw)

    if df is None:
        await update.message.reply_text("❌ Stock table kandupidikka mudiyala.")
        return

    stock_col = None
    for c in df.columns:
        if str(c).upper() in [x.upper() for x in POSSIBLE_COLUMNS]:
            stock_col = c
            break

    if stock_col is None:
        await update.message.reply_text(
            f"❌ Stock column illa.\nFound columns:\n{list(df.columns)}"
        )
        return

    symbols = [clean_symbol(x) for x in df[stock_col].dropna().tolist()]

    reply = "📊 *Groww Portfolio Analysis*\n\n"

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
