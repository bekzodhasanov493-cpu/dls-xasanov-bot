from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import CHANNEL_USERNAME


SECOND_CHANNEL_USERNAME = "@DLSXasanov10k"


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member1 = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        member2 = await bot.get_chat_member(
            chat_id=SECOND_CHANNEL_USERNAME,
            user_id=user_id
        )

        subscribed_statuses = {
            "member",
            "administrator",
            "creator"
        }

        return (
            member1.status in subscribed_statuses
            and member2.status in subscribed_statuses
        )

    except TelegramBadRequest:
        return False