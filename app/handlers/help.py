from telegram import Update
from telegram.ext import ContextTypes

from app.utils import keyboards

HELP_TEXT = (
    "ℹ️ <b>Help</b>\n\n"
    "📧 <b>Create Email</b> — generate a new temporary address\n"
    "📋 <b>My Emails</b> — see all your active addresses\n"
    "🔢 <b>Get OTP</b> — pull the latest verification code (or see the "
    "latest mail if there's no code)\n"
    "🗑 <b>Delete</b> — remove an email you no longer need\n\n"
    "New mail also gets pushed to you automatically — no need to keep "
    "checking manually.\n\n"
    "First time here? You'll need admin approval before creating emails — "
    "ask @imvrct.\n\n"
    "Use /stats anytime to see your own usage."
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT, reply_markup=keyboards.back_to_menu())


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(HELP_TEXT, parse_mode="HTML", reply_markup=keyboards.back_to_menu())
