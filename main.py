import os
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# ✅ TOKEN from Railway variable
TOKEN = os.getenv("BOT_TOKEN")

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Stock AI Bot\n\n"
        "📂 Send a CSV file with column: Symbol\n"
        "📌 Example:\nTCS.NS\nINFY.NS\nRELIANCE.NS"
    )

# ---------- CSV HANDLER ----------
async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Please upload a CSV file")
        return

    csv_file = await file.get_file()
    path = "stocks.csv"
    await csv_file.download_to_drive(path)

    df = pd.read_csv(path)

    if "Symbol" not in df.columns:
        await update.message.reply_text("❌ CSV must have 'Symbol' column")
        return

    await update.message.reply_text("🔍 Analyzing stocks...")

    for symbol in df["Symbol"]:
        symbol = str(symbol).strip()
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1mo")
            if hist.empty:
                await update.message.reply_text(f"❌ No data for {symbol}")
                continue

            price = round(hist['Close'].iloc[-1],2)
            rsi = 50  # Placeholder, future improvement
            trend = "📈 Trend unknown"  # Placeholder
            action = "⏸ HOLD"  # Placeholder

            await update.message.reply_text(
                f"📊 {symbol}\n💰 Price: {price}\n📊 Trend: {trend}\n👉 Action: {action}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error analyzing {symbol}")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
