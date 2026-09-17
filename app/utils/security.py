"""
Security helpers.

The core rule enforced everywhere in the handlers: a Telegram user may only
ever act on an alias_id that OUR database says belongs to them. alias_id
values arriving from a callback_data string are never trusted on their own.
"""

from app import database
from app.config import ADMIN_TELEGRAM_IDS

NOT_APPROVED_MESSAGE = (
    "🔒 <b>Approval needed</b>\n\n"
    "Please take approval from Admin @imvrct to use this bot.\n"
    "Thanks for stopping by! 🙏"
)


def is_admin(telegram_user_id: int) -> bool:
    return telegram_user_id in ADMIN_TELEGRAM_IDS


async def user_owns_alias(telegram_user_id: int, alias_id: str) -> bool:
    owner = await database.get_alias_owner(alias_id)
    return owner is not None and owner == telegram_user_id


async def check_approved(query, telegram_user_id: int) -> bool:
    """Call at the top of any callback that does real work (create/list/
    delete/otp). Admins always pass. Returns False (and already replies
    with the approval-needed message) if the user isn't cleared yet."""
    if is_admin(telegram_user_id) or await database.is_user_approved(telegram_user_id):
        return True
    await query.edit_message_text(NOT_APPROVED_MESSAGE, parse_mode="HTML")
    return False
