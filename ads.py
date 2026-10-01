from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiohttp import ClientSession

from database import create_ad, get_connection, delete_ad
from keyboards.main import main_menu
from config import MINI_APP_URL, HAMYON_API_KEY


router = Router()


HAMYON_URL = "https://hamyon-api.uz/payment/create"
HAMYON_SHOP_ID = "41"


def calculate_ad_fee(price):
    price = int(price)

    if price <= 200000:
        return 3000
    elif price <= 400000:
        return 4000
    else:
        return 5000


class SellAd(StatesGroup):
    waiting_photo = State()
    waiting_sale_type = State()
    waiting_price = State()
    waiting_comment = State()


def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_ad"
                )
            ]
        ]
    )


def sale_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Obmen",
                    callback_data="sale_exchange"
                ),
                InlineKeyboardButton(
                    text="💵 Naqd pulga",
                    callback_data="sale_cash"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_ad"
                )
            ]
        ]
    )


# =========================================================
# E'LON BERISH
# =========================================================

@router.callback_query(F.data == "sell_account")
async def sell_account_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.clear()
    await state.set_state(SellAd.waiting_photo)

    await callback.message.delete()

    photo = FSInputFile("assets/sample.jpg")

    sample_message = await callback.bot.send_photo(
        chat_id=callback.from_user.id,
        photo=photo,
        caption=(
            "📸 <b>Namunadagidek o‘z akkauntingiz rasmini yuboring.</b>"
        )
    )

    await state.update_data(
        sample_message_id=sample_message.message_id
    )


# =========================================================
# RASM
# =========================================================

@router.message(SellAd.waiting_photo, F.photo)
async def account_photo_handler(
    message: Message,
    state: FSMContext
):
    photo_id = message.photo[-1].file_id

    data = await state.get_data()
    sample_message_id = data.get("sample_message_id")

    if sample_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=sample_message_id
            )
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass

    await state.update_data(
        photo_id=photo_id
    )

    await state.set_state(
        SellAd.waiting_sale_type
    )

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=(
            "💰 <b>Akkauntni qanday sotasiz?</b>\n\n"
            "Sotilish turini tanlang:"
        ),
        reply_markup=sale_type_keyboard()
    )


# =========================================================
# OBMEN
# =========================================================

@router.callback_query(
    SellAd.waiting_sale_type,
    F.data == "sale_exchange"
)
async def sale_exchange_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.update_data(
        sale_type="obmen",
        price=None
    )

    await state.set_state(
        SellAd.waiting_comment
    )

    comment_message = await callback.message.edit_text(
        "📝 <b>Izoh yozing:</b>\n\n"
        "Akkaunt haqida qisqacha ma'lumot qoldiring.",
        reply_markup=cancel_keyboard()
    )

    await state.update_data(
        comment_message_id=comment_message.message_id
    )

# =========================================================
# NAQD
# =========================================================

@router.callback_query(F.data == "sale_cash")
async def sale_cash_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.update_data(
        sale_type="naqd"
    )

    await state.set_state(
        SellAd.waiting_price
    )

    price_message = await callback.message.edit_text(
        "💵 <b>Akkaunt narxini yuboring:</b>\n\n"
        "Masalan: <code>199000</code> so‘m",
        reply_markup=cancel_keyboard()
    )

    await state.update_data(
        price_message_id=price_message.message_id
    )


# =========================================================
# NARX
# =========================================================
@router.message(SellAd.waiting_price, F.text)
async def price_handler(
    message: Message,
    state: FSMContext
):
    price = message.text.strip()

    data = await state.get_data()
    price_message_id = data.get("price_message_id")

    if not price.isdigit():
        try:
            await message.delete()
        except Exception:
            pass

        if price_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=price_message_id,
                    text=(
                        "❌ <b>Narx noto‘g‘ri.</b>\n\n"
                        "Faqat raqam yuboring.\n"
                        "Masalan: <code>199000</code>"
                    ),
                    reply_markup=cancel_keyboard()
                )
            except Exception:
                pass

        return

    if price_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=price_message_id
            )
        except Exception:
            pass

    await state.update_data(
        price=price
    )

    await state.set_state(
        SellAd.waiting_comment
    )

    try:
        await message.delete()
    except Exception:
        pass

    comment_message = await message.bot.send_message(
        chat_id=message.chat.id,
        text=(
            "📝 <b>Izoh yozing:</b>\n\n"
            "Akkaunt haqida qisqacha ma'lumot qoldiring."
        ),
        reply_markup=cancel_keyboard()
    )

    await state.update_data(
        comment_message_id=comment_message.message_id
    )
# =========================================================
# IZO H / PREVIEW
# =========================================================
@router.message(SellAd.waiting_comment, F.text)
async def comment_handler(
    message: Message,
    state: FSMContext
):
    comment = message.text.strip()

    data = await state.get_data()
    comment_message_id = data.get("comment_message_id")

    if comment_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=comment_message_id
            )
        except Exception:
            pass

    await state.update_data(
        comment=comment
    )

    data = await state.get_data()

    if data["sale_type"] == "obmen":
        ad_fee = 4000
    else:
        ad_fee = calculate_ad_fee(
            data["price"]
        )

    if message.from_user.username:
        seller = f"@{message.from_user.username}"

        seller_link = (
            f'<a href="tg://user?id={message.from_user.id}">'
            f'{seller}</a>'
        )

    else:
        seller = f"ID: {message.from_user.id}"

        seller_link = (
            f'<a href="tg://user?id={message.from_user.id}">'
            f'{seller}</a>'
        )

    ad_id = create_ad(
        user_id=message.from_user.id,
        photo_id=data["photo_id"],
        sale_type=data["sale_type"],
        price=data.get("price"),
        comment=data["comment"],
        seller=seller,
        ad_fee=ad_fee
    )

    await state.update_data(ad_id=ad_id)

    try:
        await message.delete()
    except Exception:
        pass

    if data["sale_type"] == "obmen":
        tag = "#FAQAT_OBMEN"
        price_line = ""

    else:
        tag = "#SOTILADI"

        price_line = (
            f"💰 <b>Narxi:</b> "
            f"{data['price']} so'm\n"
        )

    preview_text = (
        f"🏷 <b>{tag}</b>\n"
        f"🎮 <b>DLS AKKAUNT</b>\n\n"
        f"{price_line}"
        f"👤 <b>SOTUVCHI:</b> {seller_link}\n\n"
        f"💬 <b>QO‘SHIMCHA IZOH:</b>\n"
        f"<blockquote>{comment}</blockquote>\n\n"
        f"🛡 <b>GARANT ADMINLAR:</b>\n"
        f'<blockquote>'
        f'<a href="tg://user?id=6595240938">'
        f'@khasanow17'
        f'</a>'
        f'</blockquote>\n\n'
        f"⚠️ <b>SAVDONI GARANT ADMIN BILAN QILING!</b>\n"
        f"<blockquote>"
        f"ADMINSIZ QILINGAN SAVDOLARGA "
        f"BIZ JAVOB BERMAYMIZ."
        f"</blockquote>\n\n"
        f"🤖 <b>E'LON BERISH UCHUN BOTIMIZ:</b>\n"
        f'<blockquote>'
        f'<a href="https://t.me/DLS_XASANOVBOT">'
        f'@DLS_XASANOVBOT'
        f'</a>'
        f'</blockquote>'
    )
    preview_message = await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=data["photo_id"],
        caption=preview_text
)
    payment_text = (
        "📢 <b>E'lon Shop kanalga yuborishga tayyor!</b>\n\n"
        f"💰 <b>Xizmat haqi:</b> {ad_fee:,} so‘m\n\n"
        "<blockquote>"
        "🛍 <b>Shop kanalimiz:</b> @DLS_XASANOVSHOP"
        "</blockquote>\n\n"
        "<blockquote>"
        "⏳ <b>To‘lovni 5 daqiqa ichida amalga oshiring.</b>\n"
        "Aks holda to‘lov uchun ajratilgan vaqt tugaydi va buyurtma bekor qilinadi."
        "</blockquote>\n\n"
        "<blockquote>"
        "🤖 <b>To‘lov avtomatik tasdiqlanadi</b> va tasdiqlangach, "
        "e'loningiz Shop kanalga avtomatik joylanadi."
        "</blockquote>"
    )

    payment_message = await message.bot.send_message(
        chat_id=message.chat.id,
        text=payment_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Karta raqamiga to‘lov",
                        web_app=WebAppInfo(
                            url=f"{MINI_APP_URL}?ad_id={ad_id}"
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ To‘lov qildim",
                        callback_data=f"payment_done_{ad_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                                            callback_data="cancel_ad"
                    )
                ]
            ]
        ),
        reply_to_message_id=preview_message.message_id
    )
    await state.update_data(
        payment_message_id=payment_message.message_id,
        preview_message_id=preview_message.message_id
    )

# =========================================================
# TO‘LOV / MINI APP
# =========================================================

@router.callback_query(
    F.data.startswith("create_payment_")
)
async def create_payment_handler(
    callback: CallbackQuery
):
    try:
        ad_id = int(
            callback.data.replace(
                "create_payment_",
                ""
            )
        )
    except ValueError:
        await callback.answer(
            "❌ E'lon raqami noto‘g‘ri.",
            show_alert=True
        )
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, ad_fee
        FROM ads
        WHERE id = ?
        """,
        (ad_id,)
    )

    ad = cursor.fetchone()

    conn.close()

    if not ad:
        await callback.answer(
            "❌ E'lon topilmadi.",
            show_alert=True
        )
        return

    _, ad_fee = ad

    if not ad_fee or ad_fee <= 0:
        await callback.answer(
            "❌ To‘lov summasi aniqlanmadi.",
            show_alert=True
        )
        return

    mini_app_url = (
        f"{MINI_APP_URL}?ad_id={ad_id}"
    )

    await callback.answer(
        "💳 To‘lov sahifasi ochilmoqda..."
    )

    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 To‘lovni davom ettirish",
                        web_app=WebAppInfo(
                            url=mini_app_url
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="cancel_ad"
                    )
                ]
            ]
        )
    )



# =========================================================
# AKKAUNT OLAMAN
# =========================================================

BUY_SAMPLE_PATH = "assets/buy_sample.jpg"


class BuyAd(StatesGroup):
    waiting_budget = State()
    waiting_comment = State()


@router.callback_query(F.data == "buy_account")
async def buy_account_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.clear()
    await state.set_state(BuyAd.waiting_budget)

    try:
        await callback.message.delete()
    except Exception:
        pass

    budget_message = await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            "💰 <b>BUDJETNI YUBORING:</b>\n\n"
            "Masalan: <code>199000</code> so‘m"
        ),
        reply_markup=cancel_keyboard()
    )

    await state.update_data(
        budget_message_id=budget_message.message_id
    )
@router.message(BuyAd.waiting_budget, F.text)
async def buy_budget_handler(
    message: Message,
    state: FSMContext
):
    budget = message.text.strip()

    data = await state.get_data()
    budget_message_id = data.get("budget_message_id")

    if not budget.isdigit():
        try:
            await message.delete()
        except Exception:
            pass

        if budget_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=budget_message_id,
                    text=(
                        "❌ <b>Budjet noto‘g‘ri.</b>\n\n"
                        "Faqat raqam yuboring.\n"
                        "Masalan: <code>199000</code>"
                    ),
                    reply_markup=cancel_keyboard()
                )
            except Exception:
                pass

        return

    if budget_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=budget_message_id
            )
        except Exception:
            pass

    await state.update_data(
        budget=budget
    )

    await state.set_state(
        BuyAd.waiting_comment
    )

    try:
        await message.delete()
    except Exception:
        pass

    comment_message = await message.bot.send_message(
        chat_id=message.chat.id,
        text=(
            "📝 <b>QO‘SHIMCHA IZOHNI YUBORING:</b>\n\n"
            "Qanday akkaunt kerakligini yoki boshqa talablaringizni yozing."
        ),
        reply_markup=cancel_keyboard()
    )

    await state.update_data(
        comment_message_id=comment_message.message_id
    )
@router.message(BuyAd.waiting_comment, F.text)
async def buy_comment_handler(
    message: Message,
    state: FSMContext
):
    comment = message.text.strip()

    data = await state.get_data()

    comment_message_id = data.get("comment_message_id")

    if comment_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=comment_message_id
            )
        except Exception:
            pass

    budget = data.get("budget")

    if not budget:
        await state.clear()
        await message.answer(
            "❌ Ma'lumot topilmadi. Iltimos, qaytadan e'lon bering.",
            reply_markup=main_menu()
        )
        return

    if message.from_user.username:
        seller = f"@{message.from_user.username}"
        seller_link = (
            f'<a href="tg://user?id={message.from_user.id}">'
            f'{seller}</a>'
        )
    else:
        seller = f"ID: {message.from_user.id}"
        seller_link = (
            f'<a href="tg://user?id={message.from_user.id}">'
            f'{seller}</a>'
        )

    ad_id = create_ad(
        user_id=message.from_user.id,
        photo_id=BUY_SAMPLE_PATH,
        sale_type="olish",
        price=budget,
        comment=comment,
        seller=seller,
        ad_fee=3000
    )

    await state.update_data(ad_id=ad_id)

    try:
        await message.delete()
    except Exception:
        pass

    preview_text = (
        "🏷 <b>#AKKAUNT OLAMAN</b>\n"
        "🎮 <b>DLS AKKAUNT</b>\n\n"
        f"💰 BUDJET: <b>{budget} so‘m</b>\n"
        f"👤 <b>AKKAUNT OLUVCHI:</b> {seller_link}\n\n"
        f"💬 <b>QO‘SHIMCHA IZOH:</b>\n"
        f"<blockquote>{comment}</blockquote>\n\n"
        "🛡 <b>GARANT ADMINLAR:</b>\n"
        '<blockquote>'
        '<a href="tg://user?id=6595240938">'
        '@khasanow17'
        '</a>'
        '</blockquote>\n\n'
        "⚠️ <b>SAVDONI GARANT ADMIN BILAN QILING!</b>\n"
        "<blockquote>"
        "ADMINSIZ QILINGAN SAVDOLARGA "
        "BIZ JAVOB BERMAYMIZ."
        "</blockquote>\n\n"
        "🤖 <b>ELON BERISH UCHUN BOTIMIZ:</b>\n"
        '<blockquote>'
        '<a href="https://t.me/DLS_XASANOVBOT">'
        '@DLS_XASANOVBOT'
        '</a>'
        '</blockquote>'
    )

    try:
        photo = FSInputFile(BUY_SAMPLE_PATH)
    except Exception:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=(
                "❌ <b>Preview rasmi topilmadi.</b>\n\n"
                "Iltimos, <code>assets/buy_sample.jpg</code> "
                "faylini bot papkasiga joylang."
            ),
            reply_markup=main_menu()
        )
        await state.clear()
        return

    preview_message = await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=preview_text
    )

    payment_text = (
        "📢 <b>E'lon Shop kanalga yuborishga tayyor!</b>\n\n"
        f"💰 <b>Xizmat haqi:</b> 3,000 so‘m\n\n"
        "<blockquote>"
        "🛍 <b>Shop kanalimiz:</b> @DLS_XASANOVSHOP"
        "</blockquote>\n\n"
        "<blockquote>"
        "⏳ <b>To‘lovni 5 daqiqa ichida amalga oshiring.</b>\n"
        "Aks holda to‘lov uchun ajratilgan vaqt tugaydi va buyurtma bekor qilinadi."
        "</blockquote>\n\n"
        "<blockquote>"
        "🤖 <b>To‘lov avtomatik tasdiqlanadi</b> va tasdiqlangach, "
        "e'loningiz Shop kanalga avtomatik joylanadi."
        "</blockquote>"
    )

    payment_message = await message.bot.send_message(
        chat_id=message.chat.id,
        text=payment_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Karta raqamiga to‘lov",
                        web_app=WebAppInfo(
                            url=f"{MINI_APP_URL}?ad_id={ad_id}"
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ To‘lov qildim",
                        callback_data=f"payment_done_{ad_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="cancel_ad"
                    )
                ]
            ]
        ),
        reply_to_message_id=preview_message.message_id
    )

    await state.update_data(
        payment_message_id=payment_message.message_id,
        preview_message_id=preview_message.message_id
    )

# =========================================================
# BEKOR QILISH
# =========================================================

@router.callback_query(
    F.data == "cancel_ad"
)
async def cancel_ad_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    ad_id = data.get("ad_id")
    preview_message_id = data.get("preview_message_id")

    if ad_id:
        delete_ad(
            ad_id=ad_id,
            user_id=callback.from_user.id
        )

    await callback.answer(
        "❌ E'lon bekor qilindi."
    )

    # Payment xabarini o‘chirish
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Preview xabarini o‘chirish
    if preview_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.from_user.id,
                message_id=preview_message_id
            )
        except Exception:
            pass

    await state.clear()

    # Bosh menyu
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            "🏠 <b>Bosh menyu</b>\n\n"
            "Kerakli bo‘limni tanlang:"
        ),
        reply_markup=main_menu()
    )