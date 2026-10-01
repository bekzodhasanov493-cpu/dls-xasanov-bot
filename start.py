from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from config import CHANNEL_USERNAME
from keyboards.subscription import subscription_keyboard
from keyboards.main import main_menu
from services.subscription import check_subscription


router = Router()


@router.message(F.text == "/start")
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id

    is_subscribed = await check_subscription(bot, user_id)

    if not is_subscribed:
        await message.answer(
            "🔒 <b>Botdan foydalanish uchun avval kanallarimizga obuna bo'ling.</b>\n\n"
            "<blockquote>"
"📢 Avval quyidagi kanallarga obuna bo‘ling.\n\n"
"✅ Obuna bo‘lgach, «Davom etish» tugmasini bosing."
"</blockquote>",
            reply_markup=subscription_keyboard()
        )
        return

    await message.answer(
        "👋 <b>DLS | XASANOV BOT</b> ga xush kelibsiz!"
    )

    await message.answer(
        "🏠 <b>Bosh menyu</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery,
    bot: Bot
):
    user_id = callback.from_user.id

    is_subscribed = await check_subscription(bot, user_id)

    if not is_subscribed:
        await callback.answer(
            "❌ Siz hali kanalga obuna bo‘lmagansiz.",
            show_alert=True
        )
        return

    await callback.answer("✅ Obuna tasdiqlandi!")

    await callback.message.delete()

    await bot.send_message(
        chat_id=user_id,
        text="👋 <b>DLS | XASANOV BOT</b> ga xush kelibsiz!"
    )

    await bot.send_message(
        chat_id=user_id,
        text="🏠 <b>Bosh menyu</b>\n\n"
             "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu()
    )