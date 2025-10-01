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
