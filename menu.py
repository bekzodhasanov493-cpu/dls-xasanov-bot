from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user_ads, change_ad_price, delete_ad
from keyboards.main import main_menu


router = Router()


class ChangePrice(StatesGroup):
    waiting_price = State()


def ad_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Akkount sotaman",
                    callback_data="sell_account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔵 Akkount olaman",
                    callback_data="buy_account"
                )
            ],
        ]
    )


def cancel_price_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_price"
                )
            ]
        ]
    )


@router.callback_query(F.data == "create_ad")
async def create_ad_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "➕ <b>E'lon berish</b>\n\n"
        "Qaysi turdagi e'lon bermoqchimisiz?",
        reply_markup=ad_type_keyboard()
    )


@router.callback_query(F.data == "my_ads")
async def my_ads_handler(callback: CallbackQuery):
    await callback.answer()

    ads = get_user_ads(callback.from_user.id)

    if not ads:
        await callback.message.edit_text(
            "📂 <b>E'lonlarim</b>\n\n"
            "Sizda hozircha e'lonlar mavjud emas.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ E'lon berish",
                            callback_data="create_ad"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ Bosh menyu",
                            callback_data="back_to_main"
                        )
                    ]
                ]
            )
        )
        return

    text = "📂 <b>E'lonlarim</b>\n\n"
    buttons = []

    for ad in ads:
        ad_id, sale_type, price, comment, seller, status, created_at = ad

        if sale_type == "obmen":
            sale_text = "🔄 Obmen"
        elif sale_type == "olish":
            sale_text = f"💰 Budjet: {price} so‘m"
        else:
            sale_text = f"💵 {price} so‘m"

        text += (
            f"📌 <b>E'lon #{ad_id}</b>\n"
            f"• {sale_text}\n"
            f"• 👤 {seller}\n"
            f"• 📝 {comment}\n"
            f"• 📊 Holati: {status}\n\n"
        )

        if sale_type == "naqd":
            buttons.append([
                InlineKeyboardButton(
                    text=f"💵 #{ad_id} Narxni o‘zgartirish",
                    callback_data=f"change_price_{ad_id}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                text=f"✅ #{ad_id} Sotildi",
                callback_data=f"mark_sold_{ad_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="➕ E'lon berish",
            callback_data="create_ad"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Bosh menyu",
            callback_data="back_to_main"
        )
    ])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )
@router.callback_query(F.data.startswith("change_price_"))
async def change_price_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    ad_id = int(callback.data.replace("change_price_", ""))

    ads = get_user_ads(callback.from_user.id)

    selected_ad = None

    for ad in ads:
        if ad[0] == ad_id:
            selected_ad = ad
            break

    if not selected_ad:
        await callback.message.edit_text(
            "❌ <b>E'lon topilmadi.</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ E'lonlarim",
                            callback_data="my_ads"
                        )
                    ]
                ]
            )
        )
        return

    await state.clear()
    await state.update_data(ad_id=ad_id)
    await state.set_state(ChangePrice.waiting_price)

    await callback.message.edit_text(
        f"💵 <b>E'lon #{ad_id}</b>\n\n"
        "Yangi narxni yuboring.\n\n"
        "Masalan: <code>300000</code> so‘m",
        reply_markup=cancel_price_keyboard()
    )


@router.message(ChangePrice.waiting_price, F.text)
async def new_price_handler(
    message: Message,
    state: FSMContext
):
    new_price = message.text.strip()

    data = await state.get_data()
    ad_id = data.get("ad_id")

    if not new_price.isdigit():
        await message.delete()

        await message.bot.send_message(
            chat_id=message.chat.id,
            text=(
                "❌ <b>Narx noto‘g‘ri.</b>\n\n"
                "Faqat raqam yuboring.\n"
                "Masalan: <code>300000</code>"
            ),
            reply_markup=cancel_price_keyboard()
        )
        return

    success, result = change_ad_price(
        ad_id=ad_id,
        user_id=message.from_user.id,
        new_price=new_price
    )

    try:
        await message.delete()
    except Exception:
        pass

    if not success:
        if result == "no_edits":
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=(
                    "❌ <b>Bepul narx o‘zgartirish imkoniyati tugagan.</b>\n\n"
                    "Sizda 0 ta bepul imkoniyat qoldi."
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="⬅️ E'lonlarim",
                                callback_data="my_ads"
                            )
                        ]
                    ]
                )
            )
        else:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="❌ <b>E'lon topilmadi.</b>",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="⬅️ E'lonlarim",
                                callback_data="my_ads"
                            )
                        ]
                    ]
                )
            )

        await state.clear()
        return

    await state.clear()

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=(
            "✅ <b>Narx muvaffaqiyatli o‘zgartirildi!</b>\n\n"
            f"📌 E'lon: <b>#{ad_id}</b>\n"
            f"💵 Yangi narx: <b>{new_price} so‘m</b>\n"
            f"🎁 Qolgan bepul imkoniyat: <b>{result} ta</b>\n\n"
            "📢 Kanalga chiqarish va <b>#FAST</b> belgisi "
            "keyingi bosqichda ulanadi."
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📂 E'lonlarim",
                        callback_data="my_ads"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data == "cancel_price")
async def cancel_price_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.clear()

    ads = get_user_ads(callback.from_user.id)

    if not ads:
        await callback.message.edit_text(
            "📂 <b>E'lonlarim</b>\n\n"
            "Sizda hozircha e'lonlar mavjud emas.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Bosh menyu",
                            callback_data="back_to_main"
                        )
                    ]
                ]
            )
        )
        return

    await callback.message.edit_text(
        "📂 <b>E'lonlarim</b>\n\n"
        "E'loningizni tanlang:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "🏠 <b>Bosh menyu</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu()
    )
@router.callback_query(F.data == "search_accounts")
async def search_accounts_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "🔍 <b>Akkount qidirish</b>\n\n"
        "🚧 Ushbu bo‘lim hozircha ishga tushmagan.\n\n"
        "⏳ <b>Yaqin kunlarda ishga tushadi!</b>\n\n",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
@router.callback_query(F.data == "admin")
async def admin_handler(callback: CallbackQuery):
    await callback.answer()

    admin_link = "tg://user?id=6595240938"

    await callback.message.edit_text(
        "👮 <b>BOSH ADMIN</b>\n\n"
        "👤 Admin bilan bog‘lanish uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👤 BOSH ADMIN",
                        url=admin_link
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
@router.callback_query(F.data == "ad_prices")
async def ad_prices_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "💰 <b>E'LON NARXLARI</b>\n\n"

        "📤 <b>AKKAUNT SOTISH E'LONI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💵 <code>0 – 200 000 so‘m</code>  →  <b>3 000 so‘m</b>\n"
        "💵 <code>200 001 – 400 000 so‘m</code>  →  <b>4 000 so‘m</b>\n"
        "💵 <code>400 001+ so‘m</code>  →  <b>5 000 so‘m</b>\n\n"

        "🛒 <b>AKKAUNT OLISH E'LONI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 Xizmat haqi  →  <b>3 000 so‘m</b>\n\n"

        "🔄 <b>FAQAT OBMEN E'LONI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 Xizmat haqi  →  <b>4 000 so‘m</b>\n\n"

        "<blockquote>"
        "ℹ️ Xizmat haqi e'lon kanalga joylashtirilishidan "
        "oldin to‘lanadi."
        "</blockquote>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
@router.callback_query(F.data == "rules")
async def rules_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "📚 <b>DLS | XASANOV BOT — QOIDALAR</b>\n\n"

        "🛡 <b>1. Firibgarlik qat'iyan taqiqlanadi</b>\n"
        "Boshqa foydalanuvchini aldash, soxta ma'lumot berish yoki "
        "ataylab chalg‘itish taqiqlanadi.\n\n"

        "🔐 <b>2. Maxfiy ma'lumotlarni bermang</b>\n"
        "Telegram kodi, SMS-kod, parol va boshqa shaxsiy ma'lumotlarni "
        "hech kimga yubormang. Admin bunday ma'lumotlarni so‘ramaydi.\n\n"

        "📸 <b>3. E'lon ma'lumotlari haqiqiy bo‘lishi shart</b>\n"
        "Akkaunt rasmi, holati va boshqa ko‘rsatilgan ma'lumotlar "
        "haqiqatga mos bo‘lishi kerak.\n\n"

        "💳 <b>4. Xizmat haqi oldindan to‘lanadi</b>\n"
        "E'lon kanalga joylashtirilishidan oldin belgilangan xizmat "
        "haqi to‘lanadi. To‘lov tasdiqlanmaguncha e'lon joylashtirilmaydi.\n\n"

        "⚖️ <b>5. Shubhali e'lonlar tekshiriladi</b>\n"
        "Qoidalarga zid, shubhali yoki noto‘g‘ri ma'lumotli e'lonlar "
        "admin tomonidan tekshirilishi va rad etilishi mumkin.\n\n"

        "<blockquote>"
        "⚠️ <b>Muhim:</b> Botdan foydalanish orqali ushbu qoidalarga "
        "rioya qilishga rozilik bildirgan hisoblanasiz."
        "</blockquote>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
@router.callback_query(F.data.startswith("mark_sold_"))
async def mark_sold_handler(callback: CallbackQuery):
    ad_id = int(callback.data.split("_")[-1])

    deleted = delete_ad(
        ad_id=ad_id,
        user_id=callback.from_user.id
    )

    if not deleted:
        await callback.answer(
            "❌ E'lon topilmadi.",
            show_alert=True
        )
        return

    await callback.answer(
        "✅ E'lon sotilgan deb belgilandi."
    )

    await callback.message.edit_text(
        "✅ <b>E'lon sotildi!</b>\n\n"
        "📂 E'lonlaringizdan ushbu e'lon olib tashlandi.\n"
        "📢 Shop kanaldagi e'lon esa o‘z joyida qoladi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📂 E'lonlarim",
                        callback_data="my_ads"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
@router.callback_query(F.data == "season_pass")
async def season_pass_handler(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "🎫 <b>Sezon pass xizmati</b>\n\n"
"<blockquote>Sezon pass kerak bo'lsa pastda ko'rsatilgan adminga murojat qiling.</blockquote>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👤 SEZON PASS ADMIN",
                        url="https://t.me/xasanovadmin?text=%F0%9F%91%8B%20Salom%2C%20SEZON%20PASS%20KERAK"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Bosh menyu",
                        callback_data="back_to_main"
                    )
                ]
            ]
        )
    )
