from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🌸 Gul qoshish"),
        KeyboardButton(text="💰 Balans toldirish")
    )
    builder.row(
        KeyboardButton(text="👤 Mening profilim"),
        KeyboardButton(text="📋 Mening gullarim")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🌸 Gul qoshish"),
        KeyboardButton(text="💰 Balans toldirish")
    )
    builder.row(
        KeyboardButton(text="👤 Mening profilim"),
        KeyboardButton(text="📋 Mening gullarim")
    )
    builder.row(
        KeyboardButton(text="⚙️ Admin panel")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Karta raqamini ozgartirish", callback_data="admin_change_card")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Oddiy e'lon narxini ozgartirish", callback_data="admin_change_regular_price")
    )
    builder.row(
        InlineKeyboardButton(text="🔨 Auksiyon narxini ozgartirish", callback_data="admin_change_auction_price")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Foydalanuvchiga balans qoshish", callback_data="admin_add_balance")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="💵 Daromad hisoboti", callback_data="admin_income_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="⏳ Kutilayotgan tolovlar", callback_data="admin_pending_payments")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def flower_type_first_kb() -> InlineKeyboardMarkup:
    """First step - select auction or regular sale"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Oddiy sotish", callback_data="select_regular"),
    )
    builder.row(
        InlineKeyboardButton(text="🔨 Auksiyon", callback_data="select_auction"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def flower_confirm_kb(is_auction: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_auction:
        builder.row(
            InlineKeyboardButton(text="🔨 Auksiyon (2💎)", callback_data="flower_auction"),
        )
    builder.row(
        InlineKeyboardButton(text="🛒 Sotish (1💎)", callback_data="flower_sell"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def flower_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Oddiy sotish (1💎)", callback_data="type_regular"),
    )
    builder.row(
        InlineKeyboardButton(text="🔨 Auksiyon (2💎)", callback_data="type_auction"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def auction_duration_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="30 daqiqa", callback_data="duration_30"),
        InlineKeyboardButton(text="1 soat", callback_data="duration_60"),
    )
    builder.row(
        InlineKeyboardButton(text="2 soat", callback_data="duration_120"),
        InlineKeyboardButton(text="3 soat", callback_data="duration_180"),
    )
    builder.row(
        InlineKeyboardButton(text="6 soat", callback_data="duration_360"),
        InlineKeyboardButton(text="12 soat", callback_data="duration_720"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def phone_share_kb() -> ReplyKeyboardMarkup:
    """Keyboard with phone share button"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📞 Telefon raqamni ulashish", request_contact=True)
    )
    builder.row(
        KeyboardButton(text="❌ Bekor qilish")
    )
    return builder.as_markup(resize_keyboard=True)


def regions_kb() -> InlineKeyboardMarkup:
    """Uzbekistan regions keyboard"""
    builder = InlineKeyboardBuilder()
    regions = [
        ("Toshkent shahri", "region_toshkent_shahar"),
        ("Toshkent viloyati", "region_toshkent_viloyat"),
        ("Andijon", "region_andijon"),
        ("Buxoro", "region_buxoro"),
        ("Farg'ona", "region_fargona"),
        ("Jizzax", "region_jizzax"),
        ("Xorazm", "region_xorazm"),
        ("Namangan", "region_namangan"),
        ("Navoiy", "region_navoiy"),
        ("Qashqadaryo", "region_qashqadaryo"),
        ("Samarqand", "region_samarqand"),
        ("Sirdaryo", "region_sirdaryo"),
        ("Surxondaryo", "region_surxondaryo"),
        ("Qoraqalpog'iston", "region_qoraqalpogiston"),
    ]
    
    for i in range(0, len(regions), 2):
        row = [InlineKeyboardButton(text=regions[i][0], callback_data=regions[i][1])]
        if i + 1 < len(regions):
            row.append(InlineKeyboardButton(text=regions[i+1][0], callback_data=regions[i+1][1]))
        builder.row(*row)
    
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


def topup_balance_kb() -> InlineKeyboardMarkup:
    """Balance top-up amounts"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="10,000 som", callback_data="topup_10000"),
        InlineKeyboardButton(text="20,000 som", callback_data="topup_20000"),
    )
    builder.row(
        InlineKeyboardButton(text="30,000 som", callback_data="topup_30000"),
        InlineKeyboardButton(text="50,000 som", callback_data="topup_50000"),
    )
    builder.row(
        InlineKeyboardButton(text="100,000 som", callback_data="topup_100000"),
        InlineKeyboardButton(text="200,000 som", callback_data="topup_200000"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def payment_confirm_kb(payment_id: int, user_telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{payment_id}_{user_telegram_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{payment_id}_{user_telegram_id}")
    )
    return builder.as_markup()


def auction_bid_kb(flower_id: int, current_bid: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"💰 Stavka qoyish", callback_data=f"bid_{flower_id}")
    )
    return builder.as_markup()


def flower_channel_kb(flower_id: int, is_auction: bool, seller_username: str = None, bot_username: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_auction and bot_username:
        builder.row(
            InlineKeyboardButton(
                text="🔨 Auksiyonga kirish", 
                url=f"https://t.me/{bot_username}?start=auction_{flower_id}"
            )
        )
    elif not is_auction and seller_username:
        # Regular post - show telegram link
        builder.row(
            InlineKeyboardButton(
                text="📱 Sotuvchi bilan bog'lanish", 
                url=f"https://t.me/{seller_username}"
            )
        )
    return builder.as_markup()


def auction_participant_kb(flower_id: int, is_owner: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_owner:
        builder.row(
            InlineKeyboardButton(text="🏁 Auksiyonni tugatish", callback_data=f"end_auction_{flower_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🚪 Auksiyondan chiqish", callback_data=f"leave_auction_{flower_id}")
        )
    return builder.as_markup()


def auction_sell_kb(flower_id: int, bid_id: int, bidder_telegram_id: int) -> InlineKeyboardMarkup:
    """Button for seller to sell to a specific bidder"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Sotish", 
            callback_data=f"sell_{flower_id}_{bid_id}_{bidder_telegram_id}"
        )
    )
    return builder.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")
    )
    return builder.as_markup()
