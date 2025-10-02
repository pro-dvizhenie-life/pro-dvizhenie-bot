"""Модели для Telegram бота (отдельно от основной системы анкет)."""

import enum
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Enum,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserState(enum.Enum):
    START = 'START'
    WAITING_FOR_CONSENT = 'WAITING_FOR_CONSENT'
    WAITING_FOR_APPLICANT_STATUS = 'WAITING_FOR_APPLICANT_STATUS'
    WAITING_FOR_CONTACT_PERSON = 'WAITING_FOR_CONTACT_PERSON'
    WAITING_FOR_FULL_NAME = 'WAITING_FOR_FULL_NAME'
    WAITING_FOR_BIRTH_DATE = 'WAITING_FOR_BIRTH_DATE'
    WAITING_FOR_GENDER = 'WAITING_FOR_GENDER'
    WAITING_FOR_CITY = 'WAITING_FOR_CITY'
    WAITING_FOR_PHONE = 'WAITING_FOR_PHONE'
    WAITING_FOR_EMAIL = 'WAITING_FOR_EMAIL'
    WAITING_FOR_PRODUCT = 'WAITING_FOR_PRODUCT'
    WAITING_FOR_CERTIFICATE = 'WAITING_FOR_CERTIFICATE'
    WAITING_FOR_CERTIFICATE_NUMBER = 'WAITING_FOR_CERTIFICATE_NUMBER'
    WAITING_FOR_CERTIFICATE_AMOUNT = 'WAITING_FOR_CERTIFICATE_AMOUNT'
    WAITING_FOR_CERTIFICATE_EXPIRY = 'WAITING_FOR_CERTIFICATE_EXPIRY'
    WAITING_FOR_OTHER_FUNDRAISING = 'WAITING_FOR_OTHER_FUNDRAISING'
    WAITING_FOR_OTHER_FUNDRAISING_DETAILS = 'WAITING_FOR_OTHER_FUNDRAISING_DETAILS'
    WAITING_FOR_CONSULTATION = 'WAITING_FOR_CONSULTATION'
    WAITING_FOR_CAN_PROMOTE = 'WAITING_FOR_CAN_PROMOTE'
    WAITING_FOR_PROMOTION_LINKS = 'WAITING_FOR_PROMOTION_LINKS'
    WAITING_FOR_POSITIONING_INFO = 'WAITING_FOR_POSITIONING_INFO'
    WAITING_FOR_DIAGNOSIS = 'WAITING_FOR_DIAGNOSIS'
    WAITING_FOR_HEALTH_CONDITION = 'WAITING_FOR_HEALTH_CONDITION'
    WAITING_FOR_DIAGNOSIS_DATE = 'WAITING_FOR_DIAGNOSIS_DATE'
    WAITING_FOR_TSR_PRESCRIPTION = 'WAITING_FOR_TSR_PRESCRIPTION'
    WAITING_FOR_DEADLINE = 'WAITING_FOR_DEADLINE'
    WAITING_FOR_WHY_NEEDED = 'WAITING_FOR_WHY_NEEDED'
    WAITING_FOR_MESSAGE_TO_DONORS = 'WAITING_FOR_MESSAGE_TO_DONORS'
    WAITING_FOR_VIDEO = 'WAITING_FOR_VIDEO'
    WAITING_FOR_ADDITIONAL_INFO = 'WAITING_FOR_ADDITIONAL_INFO'
    WAITING_FOR_FAMILY_INFO = 'WAITING_FOR_FAMILY_INFO'
    WAITING_FOR_INSPIRATION = 'WAITING_FOR_INSPIRATION'
    WAITING_FOR_HOBBIES = 'WAITING_FOR_HOBBIES'
    WAITING_FOR_ACHIEVEMENTS = 'WAITING_FOR_ACHIEVEMENTS'
    WAITING_FOR_FAMILY_COMPOSITION = 'WAITING_FOR_FAMILY_COMPOSITION'
    WAITING_FOR_SIBLINGS_PETS = 'WAITING_FOR_SIBLINGS_PETS'
    WAITING_FOR_FAMILY_TRADITIONS = 'WAITING_FOR_FAMILY_TRADITIONS'
    WAITING_FOR_CHILD_HOBBIES = 'WAITING_FOR_CHILD_HOBBIES'
    WAITING_FOR_CHILD_DREAM = 'WAITING_FOR_CHILD_DREAM'
    WAITING_FOR_GOSUSLUGI_CONFIRMATION = 'WAITING_FOR_GOSUSLUGI_CONFIRMATION'
    WAITING_FOR_DOCUMENTS = 'WAITING_FOR_DOCUMENTS'
    WAITING_FOR_PHOTO = 'WAITING_FOR_PHOTO'
    PREVIEW = 'PREVIEW'
    COMPLETED = 'COMPLETED'


class TelegramUser(Base):
    """Пользователь Telegram бота (отдельная таблица)."""

    __tablename__ = 'telegram_users'

    # Основные поля
    chat_id = Column(BigInteger, primary_key=True, nullable=False)
    user_name = Column(String(255))
    full_name = Column(String(255))
    birthday = Column(TIMESTAMP)
    gender = Column(String(255))
    contact_person = Column(String(255))
    phone = Column(String(32))
    email = Column(String(255))
    city = Column(String(255))

    # Продукт и статус
    product = Column(String(255))
    applicant_status = Column(String(64))

    # Сертификат
    has_certificate = Column(Boolean)
    certificate_number = Column(String(255))
    certificate_amount = Column(String(255))
    certificate_expiry = Column(String(255))

    # Фандрайзинг
    has_other_fundraising = Column(Boolean)
    other_fundraising_details = Column(Text)

    # Консультации и продвижение
    needs_consultation = Column(String(255))
    can_promote = Column(Boolean)
    promotion_links = Column(Text)
    wants_positioning_info = Column(Boolean)

    # Медицинская информация
    diagnosis = Column(String(500))
    health_condition = Column(Text)
    diagnosis_date = Column(String(255))
    has_tsr_prescription = Column(String(255))
    deadline = Column(String(500))
    why_needed = Column(Text)
    message_to_donors = Column(Text)
    wants_video = Column(Boolean)
    additional_info = Column(Text)

    # Информация о семье (взрослый)
    family_info = Column(Text)
    inspiration = Column(Text)
    hobbies = Column(Text)
    achievements = Column(Text)

    # Информация о семье (ребенок)
    family_composition = Column(Text)
    siblings_pets = Column(Text)
    family_traditions = Column(Text)
    child_hobbies = Column(Text)
    child_dream = Column(Text)

    # Документы и медиа
    image_data = Column(LargeBinary)
    has_gosuslugi = Column(Boolean)
    passport_data = Column(LargeBinary)
    snils_data = Column(LargeBinary)
    birth_certificate_data = Column(LargeBinary)
    ipra_data = Column(LargeBinary)

    # Системные поля
    confirmed_agreement = Column(Boolean, default=False)
    registered = Column(TIMESTAMP, default=datetime.utcnow)
    state = Column(Enum(UserState), default=UserState.START, nullable=False)
    utm = Column(String(255))
    resume_token = Column(String(64), unique=True)

    def __repr__(self):
        return f"<TelegramUser(chat_id={self.chat_id}, state={self.state})>"
