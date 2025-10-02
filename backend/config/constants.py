"""Константы конфигурации проекта."""

# Максимальные длины полей моделей пользователей
USER_EMAIL_MAX_LENGTH = 254
USER_PHONE_MAX_LENGTH = 32
USER_CHOICE_MAX_LENGTH = 20
USER_TELEGRAM_USERNAME_MAX_LENGTH = 100
USER_SESSION_TOKEN_MAX_LENGTH = 255

# Максимальные длины полей анкет и заявок
SURVEY_CODE_MAX_LENGTH = 64
SURVEY_TITLE_MAX_LENGTH = 200
STEP_CODE_MAX_LENGTH = 64
STEP_TITLE_MAX_LENGTH = 200
QUESTION_CODE_MAX_LENGTH = 64
QUESTION_LABEL_MAX_LENGTH = 300
QUESTION_TYPE_MAX_LENGTH = 20
OPTION_VALUE_MAX_LENGTH = 100
OPTION_LABEL_MAX_LENGTH = 200
DOCUMENT_LABEL_MAX_LENGTH = 200
APPLICATION_STATUS_MAX_LENGTH = 20
APPLICANT_TYPE_MAX_LENGTH = 20
CONSENT_TYPE_MAX_LENGTH = 50
AUDIT_ACTION_MAX_LENGTH = 50
AUDIT_TABLE_MAX_LENGTH = 50
OPTION_ORDER_DEFAULT = 0

# Ограничения на модели документов
DOCUMENT_CODE_MAX_LENGTH = 64
DOCUMENT_TITLE_MAX_LENGTH = 200
DOCUMENT_EVENT_TYPE_MAX_LENGTH = 32
DOCUMENT_VERSION_FILE_KEY_MAX_LENGTH = 512
DOCUMENT_VERSION_ORIGINAL_NAME_MAX_LENGTH = 255
DOCUMENT_VERSION_MIME_TYPE_MAX_LENGTH = 100
DOCUMENT_VERSION_STATUS_MAX_LENGTH = 20
DOCUMENT_VERSION_CHECKSUM_MAX_LENGTH = 128
DOCUMENT_VERSION_ETAG_MAX_LENGTH = 128

# Ограничения на загрузку документов
DOCUMENTS_DEFAULT_MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB
DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION = 30
DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/gif",
    "image/bmp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
)
DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS = (
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
)

# Типы заявителей
ALLOWED_APPLICANT_TYPES = ("self", "parent", "guardian", "relative")

# Названия cookies для токенов и анонимных сессий
COOKIE_ACCESS_TOKEN = "access_token"
COOKIE_REFRESH_TOKEN = "refresh_token"
COOKIE_SESSION_TOKEN = "session_token"

# Настройки пагинации API
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_COMMENTS_LIMIT = 10

# Значения по умолчанию для согласий
DEFAULT_CONSENT_TYPE = "pdn_152"

# Допустимые переходы статусов заявок
APPLICATION_STATUS_ALLOWED_TRANSITIONS = {
    "draft": ("submitted",),
    "submitted": ("under_review", "approved", "rejected"),
}

# Коды вопросов анкеты для извлечения контактных данных и согласий
APPLICATION_CONTACT_EMAIL_CODES = ("q_email",)
APPLICATION_CONTACT_PHONE_CODES = ("q_phone",)
APPLICATION_CONSENT_CODES = ("q_agree",)

# Magic link и аутентификация
MAGIC_LINK_DEFAULT_TTL_MINUTES = 60 * 24
MAGIC_LINK_TOKEN_RAW_BYTES = 32
MAGIC_LINK_TOKEN_HASH_LENGTH = 64
MAGIC_LINK_DEFAULT_RESUME_URL = "http://localhost:3000/application/resume"
MAGIC_LINK_DEFAULT_EMAIL_SUBJECT = "Продолжите заполнение заявки"
