"""
DUONIQ_FAQBot - a transparent, keyword-based FAQ bot for Telegram groups.

- Answers common questions automatically based on keywords in faqs.json
- Provides a /faq command that lists all available topics with buttons
- Lets admins reload the FAQ file on the fly with /reload (no redeploy needed)
- Never DMs anyone or claims to be a human/owner - it always identifies itself as a bot
"""

import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("DUONIQ_FAQBot")

FAQ_PATH = Path(__file__).parent / "faqs.json"


def load_faqs() -> list[dict]:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


FAQS: list[dict] = load_faqs()


def find_match(text: str) -> dict | None:
    text_lower = text.lower()
    for entry in FAQS:
        for keyword in entry.get("keywords", []):
            if keyword.lower() in text_lower:
                return entry
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hi! I'm the DUONIQ FAQ bot.\n\n"
        "I answer common questions automatically in this group. "
        "Type /faq to see everything I can help with.\n\n"
        "⚠️ Note: I'm just a bot. I will never DM you first, and no one "
        "from the team will ever ask you to send funds or private keys."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/faq - browse frequently asked questions\n"
        "/reload - (admins only) reload FAQ content from faqs.json\n\n"
        "You can also just type your question naturally in the group and "
        "I'll try to match it to a known answer."
    )


async def faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [InlineKeyboardButton(entry["question"], callback_data=str(i))]
        for i, entry in enumerate(FAQS)
    ]
    await update.message.reply_text(
        "📋 Frequently Asked Questions:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    index = int(query.data)
    if 0 <= index < len(FAQS):
        entry = FAQS[index]
        await query.edit_message_text(f"❓ {entry['question']}\n\n💬 {entry['answer']}")


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private":
        return True
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def reload_faqs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global FAQS
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Only group admins can reload the FAQ file.")
        return
    try:
        FAQS = load_faqs()
        await update.message.reply_text(f"✅ Reloaded {len(FAQS)} FAQ entries.")
    except Exception as exc:
        logger.exception("Failed to reload FAQs")
        await update.message.reply_text(f"❌ Failed to reload: {exc}")


async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    match = find_match(update.message.text)
    if match:
        await update.message.reply_text(f"💬 {match['answer']}")


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("faq", faq_menu))
    app.add_handler(CommandHandler("reload", reload_faqs))
    app.add_handler(CallbackQueryHandler(faq_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

    logger.info("DUONIQ_FAQBot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
