from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Akkount qidirish",
                    callback_data="search_accounts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ E'lon berish",
                    callback_data="create_ad"
                ),
                InlineKeyboardButton(
                    text="📂 E'lonlarim",
                    callback_data="my_ads"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰E'lon narxlari",
                    callback_data="ad_prices"
                ),
                InlineKeyboardButton(
                    text="📚 Qoidalar",
                    callback_data="rules"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎫 Sezon pass xizmati",
                    callback_data="season_pass"
                )
            ],
            [
                InlineKeyboardButton(
                   text="👮Admin",
                   callback_data="admin"
                )
            ]
        ]
    )