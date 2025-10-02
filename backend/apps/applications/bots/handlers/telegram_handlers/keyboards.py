from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def yes_no_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data="YES"),
            InlineKeyboardButton("❌ Нет", callback_data="NO")
        ]
    ])

def resume_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Продолжить", callback_data="RESUME_BUTTON"),
            InlineKeyboardButton("Начать заново", callback_data="RESTART_BUTTON")
        ]
    ])

def product_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Коляска (ТСР)", callback_data="PRODUCT_WHEELCHAIR"),
            InlineKeyboardButton("Приставка", callback_data="PRODUCT_CONSOLE"),
            InlineKeyboardButton("Комплектующие", callback_data="PRODUCT_PARTS")
        ]
    ])

def consultation_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да, по ИПРА", callback_data="CONSULT_IPRA"),
            InlineKeyboardButton("Да, по МСЭ", callback_data="CONSULT_MSE")
        ],
        [
            InlineKeyboardButton("Да, по СФР", callback_data="CONSULT_SFR"),
            InlineKeyboardButton("Нет", callback_data="CONSULT_NO")
        ]
    ])

def applicant_status_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Я и есть подопечный", callback_data="APPLICANT_SELF"),
            InlineKeyboardButton("Мать/отец", callback_data="APPLICANT_PARENT")
        ],
        [
            InlineKeyboardButton("Опекун", callback_data="APPLICANT_GUARDIAN"),
            InlineKeyboardButton("Родственник", callback_data="APPLICANT_RELATIVE")
        ]
    ])

def gender_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Мужской", callback_data="GENDER_MALE"),
            InlineKeyboardButton("Женский", callback_data="GENDER_FEMALE")
        ]
    ])
