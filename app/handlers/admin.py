import logging

from telegram import Update
from telegram.ext import ContextTypes

from app import database
from app.utils.security import is_admin

logger = logging.getLogger("tempmail.handlers.admin")

ADMIN_ONLY_TEXT = "❌ This command is for admins only."


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Personal stats — available to any user, matches item 17 of the spec."""
    user = update.effective_user
    row = await database.get_stats(user.id)
    aliases = await database.list_aliases(user.id)

    emails_received = row["emails_received"] if row else 0
    otps_found = row["otps_found"] if row else 0

    text = (
        "📊 <b>Your Statistics</b>\n\n"
        f"📧 Active Emails: {len(aliases)}\n"
        f"📩 Emails Received: {emails_received}\n"
        f"🔢 OTPs Found: {otps_found}"
    )
    await update.message.reply_html(text)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return

    totals = await database.admin_totals()
    text = (
        "🛠 <b>Admin Dashboard</b>\n\n"
        f"👥 Total users: {totals['users']}\n"
        f"📧 Total aliases: {totals['aliases']}\n"
        f"📩 API status: use /health\n"
        f"⚡ Recent errors: check server logs\n\n"
        "Commands: /stats /users /broadcast /host /health /ok /delete"
    )
    await update.message.reply_html(text)


async def ok_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ok <telegram_id> — approves a user; they get notified automatically."""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return

    if not context.args:
        await update.message.reply_text("Usage: /ok <telegram_id>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ That doesn't look like a valid Telegram ID (should be a number).")
        return

    await database.set_approval(target_id, True)

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🎉 <b>Congratulations!</b>\n\n"
                "Your account has been approved ✅\n"
                "You can now use all bot features — try 📧 Create Email!"
            ),
            parse_mode="HTML",
        )
        notified = True
    except Exception:
        logger.exception("failed to notify approved user %s", target_id)
        notified = False

    note = "" if notified else "\n⚠️ Couldn't message them directly (they may not have started the bot yet)."
    await update.message.reply_text(f"✅ Approved user {target_id}.{note}")


async def delete_approval_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/delete <telegram_id> — revokes a user's approval."""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return

    if not context.args:
        await update.message.reply_text("Usage: /delete <telegram_id>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ That doesn't look like a valid Telegram ID (should be a number).")
        return

    await database.set_approval(target_id, False)
    await update.message.reply_text(f"🚫 Approval removed for user {target_id}.")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return
    totals = await database.admin_totals()
    await update.message.reply_text(f"👥 Total users: {totals['users']}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return

    message_text = " ".join(context.args) if context.args else ""
    if not message_text:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    conn = database._get_conn()
    rows = conn.execute("SELECT telegram_user_id FROM users").fetchall()

    sent, failed = 0, 0
    for row in rows:
        try:
            await context.bot.send_message(chat_id=row["telegram_user_id"], text=f"📢 {message_text}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📢 Broadcast sent to {sent} users ({failed} failed).")


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Runs a real end-to-end test right now and reports back in Telegram —
    no need to open the Render dashboard to see what's going wrong.
    """
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return

    from app.inboxmail import client, InboxMailError, pick_field

    lines = ["🩺 <b>Health Check</b>", ""]

    try:
        domains = await client.list_domains()
        lines.append(f"📩 InboxMail API: ✅ reachable ({len(domains)} domain(s) visible)")
    except InboxMailError as exc:
        lines.append(f"📩 InboxMail API: ❌ {exc}")

    aliases = await database.list_aliases(user.id)
    if not aliases:
        lines.append(
            "\n📧 You (admin) have no aliases yet — create one with 📧 Create "
            "Email, send it a test mail, then run /health again to test the "
            "logs lookup end-to-end."
        )
    else:
        alias = aliases[0]
        lines.append(f"\n📧 Testing latest alias: {alias['email_address']}")
        try:
            messages = await client.get_alias_logs(alias["alias_id"])
            lines.append(f"📥 get_alias_logs: ✅ {len(messages)} message(s) found")
            if messages:
                m = messages[0]
                sender = pick_field(m, "sender", default="?")
                subject = pick_field(m, "subject", default="?")
                status = pick_field(m, "status", default="?")
                direction = pick_field(m, "direction", default="?")
                lines.append(
                    f"   Latest → from: {sender} | subject: {subject} | "
                    f"status: {status} | direction: {direction}"
                )
            else:
                lines.append(
                    "   No inbound mail logged for this alias yet — send a "
                    "test email to it, wait a few seconds, then run /health again."
                )
        except InboxMailError as exc:
            lines.append(f"📥 get_alias_logs: ❌ {exc}")

    await update.message.reply_html("\n".join(lines))
