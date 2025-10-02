"""Настройки базы данных для Telegram бота."""

from django.conf import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def init_telegram_db():
    """Инициализация подключения к БД для Telegram бота."""

    # Берем настройки из Django
    db_config = settings.DATABASES['default']

    # Поддержка SQLite и PostgreSQL
    if db_config['ENGINE'] == 'django.db.backends.sqlite3':
        db_url = f"sqlite:///{db_config['NAME']}"
    else:
        # PostgreSQL
        db_url = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"

    engine = create_engine(db_url)

    # Создаем таблицы из telegram_models
    from backend.apps.applications.bots.telegram_models import Base
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal
