import os
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CHOOSING, COIN_CHOOSING, AMOUNT, TXID_STEP, PHOTO_STEP, CRYPTO_SOURCE_COIN, PSC_CODE, WALLET_STEP, PSC_PHOTO, TEAM_APP, RATING = range(11)

# ---------------- DATABASE ----------------

conn = sqlite3.connect("queue.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    exchange_type TEXT,
    source_coin TEXT,
    dest_coin TEXT,
    amount REAL,
    fee REAL,
    final REAL,
    psc_code TEXT,
    txid TEXT,
    wallet TEXT
)
""")
conn.commit()

# ---------------- CONFIG ----------------

EXCHANGE_TYPES = {
    "paypal_crypto": "💳 PayPal ➜ Crypto",
    "crypto_paypal": "🪙 Crypto ➜ PayPal",
    "realtime_crypto": "🏦 Echtzeit ➜ Crypto",
    "crypto_realtime": "🪙 Crypto ➜ Echtzeit",
    "crypto_crypto": "🪙 Crypto ➜ Crypto",
    "psc_crypto": "🎮 PSC ➜ Crypto",
}

FEES = {
    "paypal_crypto": 0.15,
    "crypto_paypal": 0.15,
    "realtime_crypto": 0.15,
    "crypto_realtime": 0.15,
    "crypto_crypto": 0.045,
    "psc_crypto": 0.15,
}

COINS = {
    "btc": "₿ Bitcoin (BTC)",
    "eth": "Ξ Ethereum (ETH)",
    "ltc": "Ł Litecoin (LTC)",
    "sol": "◎ Solana (SOL)"
}

WALLETS = {
    "btc": "bc1qmcun9azx3c5a8gex5r9ed732v2aertw647mqtv",
    "eth": "0xa4bBaE07d8A61e5b8df74D4f82F96EBCdebfa05c",
    "ltc": "LKLHfij43e7iWdKug22ZoYbWtC7qFdq42i",
    "sol": "3b9aTrZ64VZYV7bye1fhnDu65BEgxvpH5Kj2pKkfPqZA"
}

PAYPAL_EMAIL = "onisha.sha.k.e.i.a37.36@gmail.com"

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(text, callback_data=key)]
        for key, text in EXCHANGE_TYPES.items()
    ]
    keyboard.append([InlineKeyboardButton("💼 Team Bewerbung", callback_data="team_apply")])

    await update.message.reply_text(
        "🤖 *Automatic Exchange* 🤖\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✨ *Service by @golfbat*\n"
        "📞 *Support: @golfbat*\n\n"
        "🚀 *Deine Vorteile:*\n"
        "• ⚡ Blitzschnelle Abwicklung\n"
        "• 🔒 100% Sicher & Diskret\n"
        "• 💎 Premium Support\n\n"
        "💸 *Service Fees:*\n"
        "• Echtzeit ➜ Crypto: 15%\n"
        "• PayPal ➜ Crypto: 15%\n"
        "• PSC ➜ Crypto: 15%\n"
        "• Crypto ➜ Echtzeit: 15%\n"
        "• Crypto ➜ Crypto: 4.5%\n\n"
        "Wähle jetzt deine Exchange-Art aus dem Menü unten:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CHOOSING

# ---------------- EXCHANGE WAHL ----------------

async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "team_apply":
        await query.edit_message_text(
            "💼 *Team Bewerbung*\n\n"
            "Wir suchen erfahrene Exchanger für unser Admin-Team!\n\n"
            "Bitte schreibe eine kurze Bewerbung (Erfahrung, Verfügbarkeit, etc.):",
            parse_mode="Markdown"
        )
        return TEAM_APP

    exchange_key = query.data
    context.user_data["exchange_key"] = exchange_key
    context.user_data["exchange"] = EXCHANGE_TYPES[exchange_key]

    if exchange_key == "crypto_crypto":
        keyboard = [[InlineKeyboardButton(text, callback_data=key)] for key, text in COINS.items()]
        await query.edit_message_text(
            "🪙 Welche Coin möchtest du *senden*?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return CRYPTO_SOURCE_COIN
    else:
        keyboard = [[InlineKeyboardButton(text, callback_data=key)] for key, text in COINS.items()]
        await query.edit_message_text(
            f"✅ Gewählt: {context.user_data['exchange']}\n\n"
            "🪙 Welche Crypto Coin möchtest du *erhalten*?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return COIN_CHOOSING

# ---------------- CRYPTO SOURCE COIN ----------------

async def choose_source_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    coin_key = query.data
    context.user_data["source_coin_key"] = coin_key
    context.user_data["source_coin"] = COINS[coin_key]
    context.user_data["source_wallet"] = WALLETS[coin_key]

    keyboard = [[InlineKeyboardButton(text, callback_data=key)] for key, text in COINS.items()]
    await query.edit_message_text(
        f"✅ Sende: {context.user_data['source_coin']}\n\n"
        "🪙 Welche Coin möchtest du *erhalten*?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return COIN_CHOOSING

# ---------------- COIN WAHL (DESTINATION) ----------------

async def choose_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    coin_key = query.data
    context.user_data["dest_coin_key"] = coin_key
    context.user_data["dest_coin"] = COINS[coin_key]
    context.user_data["dest_wallet"] = WALLETS[coin_key]

    exchange_key = context.user_data.get("exchange_key")

    if exchange_key == "psc_crypto":
        await query.edit_message_text(
            f"🎮 PSC ➜ {context.user_data['dest_coin']}\n\n"
            "Bitte sende jetzt deinen *PaySafeCard Code*:",
            parse_mode="Markdown"
        )
        return PSC_CODE
    elif exchange_key == "paypal_crypto":
        await query.edit_message_text(
            f"💳 PayPal ➜ {context.user_data['dest_coin']}\n\n"
            f"Bitte sende den Betrag an folgende PayPal E-Mail:\n`{PAYPAL_EMAIL}`\n\n"
            "Gib danach den gesendeten *Betrag* ein (nur Zahl):",
            parse_mode="Markdown"
        )
        return AMOUNT
    elif exchange_key == "crypto_crypto":
        await query.edit_message_text(
            f"🪙 {context.user_data['source_coin']} ➜ {context.user_data['dest_coin']}\n\n"
            "💰 Betrag eingeben (nur Zahl):",
            parse_mode="Markdown"
        )
        return AMOUNT
    else:
        await query.edit_message_text(
            f"🪙 Coin: {context.user_data['dest_coin']}\n\n"
            "💰 Betrag eingeben (nur Zahl):",
            parse_mode="Markdown"
        )
        return AMOUNT

# ---------------- PSC CODE ----------------

async def receive_psc_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["psc_code"] = update.message.text
    await update.message.reply_text(
        "📸 Bitte sende jetzt ein *Foto vom Bon* (PSC Beleg):",
        parse_mode="Markdown"
    )
    return PSC_PHOTO

async def receive_psc_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    context.user_data["psc_photo_id"] = photo.file_id
    await update.message.reply_text(
        "💰 Bitte gib den *Betrag* der PSC ein (10€ - 999€):",
        parse_mode="Markdown"
    )
    return AMOUNT

# ---------------- BETRAG ----------------

async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount_value = float(update.message.text.replace(",", "."))
        if amount_value < 10 or amount_value > 999:
            await update.message.reply_text("❌ Der Betrag muss zwischen *10€* und *999€* liegen.", parse_mode="Markdown")
            return AMOUNT
    except Exception:
        await update.message.reply_text("❌ Bitte eine gültige Zahl eingeben.")
        return AMOUNT

    exchange_key = context.user_data.get("exchange_key")
    fee_rate = FEES.get(exchange_key, 0.15)

    fee = round(amount_value * fee_rate, 2)
    final = round(amount_value - fee, 2)

    context.user_data["amount"] = amount_value
    context.user_data["fee"] = fee
    context.user_data["final"] = final

    if exchange_key in ["psc_crypto", "paypal_crypto", "crypto_crypto", "realtime_crypto", "crypto_paypal", "crypto_realtime"]:
        await update.message.reply_text(
            "🏦 Bitte sende jetzt deine *Wallet-Adresse* (oder PayPal E-Mail / IBAN), auf der du den Betrag erhalten möchtest:",
            parse_mode="Markdown"
        )
        return WALLET_STEP
    else:
        return await finalize_request(update, context)

# ---------------- WALLET STEP ----------------

async def receive_user_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_wallet"] = update.message.text
    return await finalize_request(update, context)

async def finalize_request(update, context):
    user = update.effective_user
    username = user.username or "NoUsername"
    exchange_key = context.user_data.get("exchange_key")
    amount_value = context.user_data["amount"]
    fee = context.user_data["fee"]
    final = context.user_data["final"]
    dest_coin = context.user_data.get("dest_coin")
    source_coin = context.user_data.get("source_coin", "N/A")
    psc_code = context.user_data.get("psc_code", "N/A")
    user_wallet = context.user_data.get("user_wallet", "N/A")

    cursor.execute(
        "INSERT INTO queue (user_id, username, exchange_type, source_coin, dest_coin, amount, fee, final, psc_code, wallet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user.id,
            username,
            context.user_data["exchange"],
            source_coin,
            dest_coin,
            amount_value,
            fee,
            final,
            psc_code,
            user_wallet
        ),
    )
    conn.commit()
    ticket_id = cursor.lastrowid

    # Admin Notification
    admin_text = (
        f"🚨 *Neue Anfrage #{ticket_id}*\n\n"
        f"👤 @{username} (ID: `{user.id}`)\n"
        f"🔄 {context.user_data['exchange']}\n"
        f"📥 Erhält: {final}€ {'PayPal/Realtime' if 'paypal' in exchange_key or 'realtime' in exchange_key else dest_coin}\n"
        f"💰 Betrag: {amount_value}€\n"
        f"💸 Fee: {fee}€\n"
        f"✅ Auszahlung: {final}€\n"
        f"🏦 User Payout: `{user_wallet}`\n"
    )
    if exchange_key == "psc_crypto":
        admin_text += f"🎮 PSC Code: `{psc_code}`\n"
        psc_photo_id = context.user_data.get("psc_photo_id")
        if psc_photo_id:
            try:
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=psc_photo_id, caption=f"📄 PSC Beleg für Ticket #{ticket_id}")
            except Exception as e:
                print(f"Error sending PSC photo to admin: {e}")
    elif exchange_key == "crypto_crypto":
        admin_text += f"📤 Sendet: {source_coin}\n"
    elif "crypto" in exchange_key and ("paypal" in exchange_key or "realtime" in exchange_key):
        admin_text += f"📤 Sendet: {dest_coin}\n"

    keyboard = [[InlineKeyboardButton("✅ Erledigt", callback_data=f"done_{ticket_id}"),
                 InlineKeyboardButton("❌ Ablehnen", callback_data=f"deny_{ticket_id}")]]

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Error sending notification to admin: {e}")

    # User Response
    user_text = (
        f"🎟 *Ticket #{ticket_id} erstellt!*\n\n"
        f"💸 Fee: {fee}€\n"
        f"✅ Du erhältst: {final}€ {dest_coin}\n\n"
    )

    if exchange_key == "crypto_crypto":
        source_wallet = WALLETS.get(context.user_data.get("source_coin_key"), "N/A")
        user_text += f"📥 Bitte sende {amount_value}€ in {source_coin} an:\n`{source_wallet}`\n\n"
    elif exchange_key == "paypal_crypto":
        user_text += f"💳 Bitte sende {amount_value}€ via PayPal (Freunde & Familie) an:\n`{PAYPAL_EMAIL}`\n\n"
    elif exchange_key == "realtime_crypto":
        user_text += "🏦 Bitte kontaktiere @golfbat für die Echtzeit-Zahlungsdaten.\n\n"
    elif "crypto" in exchange_key and ("paypal" in exchange_key or "realtime" in exchange_key):
        # The user sends the crypto coin they selected as destination during setup (e.g. BTC)
        # In the Crypto -> PayPal flow, 'dest_coin_key' was used to store what they send.
        source_wallet = WALLETS.get(context.user_data.get("dest_coin_key"), "N/A")
        user_text += f"📥 Bitte sende {amount_value}€ in {dest_coin} an:\n`{source_wallet}`\n\n"

    user_text += "📌 *Bitte sende jetzt die Transaktions-Bestätigung (TXID oder Screenshot):*"

    await update.message.reply_text(user_text, parse_mode="Markdown")
    return TXID_STEP

# ---------------- TEAM APP ----------------

async def team_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    app_text = update.message.text

    admin_msg = (
        f"💼 *Neue Team-Bewerbung*\n\n"
        f"👤 Von: @{user.username} (ID: `{user.id}`)\n\n"
        f"📝 Text:\n{app_text}"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    await update.message.reply_text("✅ Deine Bewerbung wurde an das Admin-Team gesendet. Wir melden uns!", parse_mode="Markdown")
    return ConversationHandler.END

# ---------------- TXID & CONFIRMATIONS ----------------

async def receive_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text
    context.user_data["txid"] = txid

    await update.message.reply_text(
        f"✅ *TXID `{txid}` empfangen!*\n\n"
        "🔍 *Blockchain Status:*\n"
        "⏳ Confirmations: 0/3 (Wird geprüft...)\n\n"
        "📸 Bitte sende jetzt einen *Screenshot* der Transaktion.",
        parse_mode="Markdown"
    )
    return PHOTO_STEP

# ---------------- PHOTO STEP ----------------

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file_id = photo.file_id

    caption = (
        f"📸 *Neuer Screenshot von @{user.username}*\n"
        f"🆔 User-ID: `{user.id}`\n"
        f"🔗 TXID: `{context.user_data.get('txid', 'N/A')}`"
    )

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error forwarding photo to admin: {e}")

    await update.message.reply_text(
        "🚀 *Bild erfolgreich an den Support gesendet!*\n\n"
        "⏳ Wir prüfen deine Transaktion nun. Du erhältst eine Nachricht, sobald der Status aktualisiert wurde.\n\n"
        "⭐️ *Bewertung:* Wie zufrieden bist du? (1-5)",
        parse_mode="Markdown"
    )

    return RATING

async def receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text
    user = update.effective_user

    admin_msg = f"⭐ *Neue Bewertung*\n👤 @{user.username}: {rating}/5 Sterne"
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")

    await update.message.reply_text("🙏 Danke für deine Bewertung! Bis zum nächsten Mal.\n\n📞 @golfbat Safe Auto Deal", parse_mode="Markdown")
    return ConversationHandler.END

# ---------------- ADMIN REPLY ----------------

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != ADMIN_ID:
        return

    if update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption
        if text and "🆔" in text:
            try:
                user_id_line = [line for line in text.split("\n") if "🆔" in line][0]
                user_id = int(user_id_line.split("`")[1])

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💬 *Support Antwort:*\n\n{update.message.text}\n\n📞 @golfbat",
                    parse_mode="Markdown"
                )
                await update.message.reply_text("✅ Antwort gesendet.")
            except Exception as e:
                print(f"Error in admin_reply: {e}")
                await update.message.reply_text("❌ Fehler beim Senden der Antwort.")

# ---------------- ADMIN BUTTONS ----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data
    action, ticket_id = data.split("_")

    cursor.execute("SELECT user_id FROM queue WHERE id=?", (ticket_id,))
    row = cursor.fetchone()
    if not row:
        return

    user_id = row[0]

    if action == "done":
        await context.bot.send_message(user_id, "✅ Deine Transaktion wurde bestätigt und abgeschlossen!\n\n@golfbat Safe Auto Deal")
        await query.edit_message_text(f"✅ Ticket #{ticket_id} als ERLEDIGT markiert.")
    elif action == "deny":
        await context.bot.send_message(user_id, "❌ Deine Transaktion wurde abgelehnt. Bitte kontaktiere den Support @golfbat.")
        await query.edit_message_text(f"❌ Ticket #{ticket_id} ABGELEHNT.")

# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(choose)],
            CRYPTO_SOURCE_COIN: [CallbackQueryHandler(choose_source_coin)],
            COIN_CHOOSING: [CallbackQueryHandler(choose_coin)],
            PSC_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_psc_code)],
            PSC_PHOTO: [MessageHandler(filters.PHOTO, receive_psc_photo)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount)],
            WALLET_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_wallet)],
            TXID_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_txid)],
            PHOTO_STEP: [MessageHandler(filters.PHOTO, receive_photo)],
            TEAM_APP: [MessageHandler(filters.TEXT & ~filters.COMMAND, team_application)],
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rating)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(done_|deny_)"))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, admin_reply))

    print("🚀 Ultra Exchange Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    main()
