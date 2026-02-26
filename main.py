import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Config
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "DEIN_TOKEN_HIER")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "DEINE_ADMIN_ID_HIER"))

# Datenbank Setup
def init_db():
    conn = sqlite3.connect("exchange.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_config (
        user_id INTEGER PRIMARY KEY,
        ltc_address TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        psc_code TEXT,
        amount REAL,
        fee REAL,
        final REAL,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# States
USER_STATE = {}
STATE_WAITING_PSC = "WAITING_PSC"
STATE_WAITING_AMOUNT = "WAITING_AMOUNT"
STATE_WAITING_LTC_SAVE = "WAITING_LTC_SAVE"

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Willkommen bei AcksonP2C!**\n\n"
        "Hier kannst du deine Paysafecard-Codes automatisch einlösen und dein Guthaben in LTC auszahlen lassen.\n\n"
        "📋 **Kurzanleitung:**\n"
        "1️⃣ Tippe auf 💳 **Code einlösen** und sende deinen 16-stelligen Code\n"
        "2️⃣ Warte kurz (~1 Min) bis der Code geprüft wird\n"
        "3️⃣ Speichere deine LTC-Adresse unter 🔑 **LTC-Adresse speichern**\n"
        "4️⃣ Zahle dein Guthaben aus mit 📤 **Guthaben auszahlen**\n\n"
        "💸 **Gebühren:**\n"
        "• ab 15 €   → 20% Gebühr\n"
        "• ab 1000 €  → 15% Gebühr\n\n"
        "👤 Service by @A_Ackson_Backup\n"
        "🛠 Support @A_Ackson_Backup"
    )
    keyboard = [
        [InlineKeyboardButton("💳 Code einlösen", callback_data='start_exchange')],
        [InlineKeyboardButton("🔑 LTC-Adresse speichern", callback_data='save_ltc')],
        [InlineKeyboardButton("📤 Guthaben auszahlen", callback_data='payout')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# Button Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'start_exchange':
        USER_STATE[user_id] = {'state': STATE_WAITING_PSC}
        await query.edit_message_text("💳 Bitte sende mir deinen **16-stelligen PaySafeCard Code**. 📝", parse_mode='Markdown')
    
    elif query.data == 'save_ltc':
        USER_STATE[user_id] = {'state': STATE_WAITING_LTC_SAVE}
        await query.edit_message_text("🔑 Bitte sende mir deine **LTC-Adresse**, die gespeichert werden soll.", parse_mode='Markdown')

    elif query.data == 'payout':
        conn = sqlite3.connect("exchange.db")
        cursor = conn.cursor()
        cursor.execute("SELECT ltc_address FROM user_config WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            await query.edit_message_text("❌ Du hast noch keine LTC-Adresse gespeichert. Bitte nutze zuerst '🔑 LTC-Adresse speichern'.")
        else:
            await query.edit_message_text(f"📤 Auszahlung angefordert an Adresse: `{row[0]}`\n\nEin Admin wird die Auszahlung prüfen.", parse_mode='Markdown')
            # Hier könnte man eine Admin-Benachrichtigung für die Auszahlung einbauen

    elif query.data.startswith('accept_') or query.data.startswith('decline_'):
        if query.from_user.id != ADMIN_ID:
            return
        action, order_id = query.data.split('_')
        order_id = int(order_id)

        conn = sqlite3.connect("exchange.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, final FROM orders WHERE id=?", (order_id,))
        row = cursor.fetchone()
        if row:
            target_user_id, final_amount = row
            if action == 'accept':
                cursor.execute("UPDATE orders SET status='ACCEPTED' WHERE id=?", (order_id,))
                await context.bot.send_message(target_user_id,
                    f"✅ Deine Anfrage wurde akzeptiert. Auszahlung von {final_amount}€ in LTC erfolgt bald! 🚀"
                )
                await query.edit_message_text(f"✅ Anfrage #{order_id} akzeptiert.")
            else:
                cursor.execute("UPDATE orders SET status='DECLINED' WHERE id=?", (order_id,))
                await context.bot.send_message(target_user_id,
                    "❌ Deine Anfrage wurde abgelehnt. Support: @A_Ackson_Backup"
                )
                await query.edit_message_text(f"❌ Anfrage #{order_id} abgelehnt.")
        conn.commit()
        conn.close()

# Message Handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USER_STATE:
        return

    state_data = USER_STATE[user_id]
    current_state = state_data.get('state')

    if current_state == STATE_WAITING_LTC_SAVE:
        ltc_addr = update.message.text
        conn = sqlite3.connect("exchange.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_config (user_id, ltc_address) VALUES (?, ?)", (user_id, ltc_addr))
        conn.commit()
        conn.close()
        del USER_STATE[user_id]
        await update.message.reply_text(f"✅ LTC-Adresse gespeichert: `{ltc_addr}`", parse_mode='Markdown')

    elif current_state == STATE_WAITING_PSC:
        state_data['psc_code'] = update.message.text
        state_data['state'] = STATE_WAITING_AMOUNT
        await update.message.reply_text("💰 Betrag der PaySafeCard eingeben (nur Zahl):", parse_mode='Markdown')

    elif current_state == STATE_WAITING_AMOUNT:
        try:
            amount = float(update.message.text)
            if amount < 15:
                await update.message.reply_text("❌ Mindestbetrag ist 15€.")
                return
            
            fee_percent = 0.20 if amount < 1000 else 0.15
            fee = round(amount * fee_percent, 2)
            final = round(amount - fee, 2)
            
            # Get stored LTC address
            conn = sqlite3.connect("exchange.db")
            cursor = conn.cursor()
            cursor.execute("SELECT ltc_address FROM user_config WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            
            ltc_address = row[0] if row else "Nicht gespeichert"
            
            cursor.execute("""
                INSERT INTO orders (user_id, username, psc_code, amount, fee, final, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, update.effective_user.username, state_data['psc_code'], 
                  amount, fee, final, 'PENDING'))
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Send to Admin
            admin_text = (
                f"📥 *Neue Exchange Anfrage #{order_id}*\n\n"
                f"👤 @{update.effective_user.username} (ID: {user_id})\n"
                f"🪙 LTC (gespeichert): `{ltc_address}`\n"
                f"💳 PSC: `{state_data['psc_code']}`\n"
                f"💰 Betrag: {amount}€\n"
                f"💸 Fee: {fee}€ ({int(fee_percent*100)}%)\n"
                f"✅ Auszahlung: {final}€\n\n"
                f"Bitte prüfen:"
            )
            keyboard = [[
                InlineKeyboardButton("✅ Akzeptieren", callback_data=f"accept_{order_id}"),
                InlineKeyboardButton("❌ Ablehnen", callback_data=f"decline_{order_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=reply_markup, parse_mode='Markdown')

            await update.message.reply_text(
                f"⏳ Code eingereicht! (~1 Min Prüfung)\n\n"
                f"📊 Zusammenfassung:\n"
                f"Betrag: {amount}€\n"
                f"Gebühr: {fee}€\n"
                f"Auszahlung: {final}€\n\n"
                f"Warte auf Bestätigung durch den Admin.",
                parse_mode='Markdown'
            )
            del USER_STATE[user_id]
            
        except ValueError:
            await update.message.reply_text("❌ Ungültiger Betrag, nur Zahlen eingeben.")

# Main
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    import asyncio
    async def main():
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        print("Bot läuft...")
        # Keep alive
        while True:
            await asyncio.sleep(10)

    asyncio.run(main())
