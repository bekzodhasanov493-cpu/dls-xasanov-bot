import asyncio
import logging

from aiogram import Bot, Dispatcher
from handlers.ads import router as ads_router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db

from handlers.start import router as start_router
from handlers.menu import router as menu_router


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida topilmadi!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(ads_router)

    init_db()

    print("✅ DLS | XASANOV BOT ishga tushdi!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())