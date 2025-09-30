# Чат-бот для Благотворительного Фонда «Движение»
Бот для автоматизации сбора заявок от подопечных и их представителей. Встроенная интеграция с сайтом [dvizhenie.life](https://dvizhenie.life).

## Цель проекта
- Сократить время обработки заявок сотрудниками фонда
- Сделать процесс заполнения анкеты удобным для пользователя
- Обеспечить соответствие требованиям 152-ФЗ «О персональных данных»

## Основные функции
### Для пользователей
- **Пошаговое заполнение анкеты** с динамическими шагами и условиями видимости вопросов
- **Сохранение черновиков** и возможность вернуться к заполнению позже по `session_token`
- **Регистрация и вход** по email/телефону с JWT и cookie-токенами
- **Отправка согласий** с фиксацией IP-адреса и таймстемпа
### Для администраторов
- **Просмотр и поиск заявок** с пагинацией и фильтрами по статусу, анкете, email/телефону
- **Изменение статуса** с журналированием истории
- **Комментирование заявок** и пометка срочных комментариев
- **Экспорт заявок в CSV** с ответами на вопросы анкеты

## API-обзор (v1)
- `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/users/me`
- `/api/v1/applications/forms/<survey_code>/sessions/` — создание сессии и старт черновика
- `/api/v1/applications/forms/<public_id>/draft/` — просмотр и обновление черновика
- `/api/v1/applications/forms/<public_id>/next/`, `/submit/`, `/consents/`
- `/api/v1/applications/forms/<public_id>/comments/` — чтение и добавление комментариев
- `/api/v1/applications/admin/applications/…` — административные листинги, статусы и таймлайн
- `/api/v1/applications/admin/export.csv` — потоковый экспорт данных
- `/api/v1/documents/uploads/` — выдача presigned-подписей на загрузку файлов
- `/api/v1/documents/uploads/<version_id>/complete/` — фиксация завершённой загрузки
- `/api/v1/documents/applications/<public_id>/` — список документов заявки
- `/api/v1/documents/<document_id>/` — архивирование/удаление документа

## Настройка окружения
- Скопируйте `.env.example` в `.env` и заполните переменные:
  - `DJANGO_SUPERUSER_EMAIL` и `DJANGO_SUPERUSER_PASSWORD` — будут использованы для
    автоматического создания суперпользователя после применения миграций.
  - `DJANGO_SUPERUSER_CREATE` можно выставить в `False`, если автоматическое
    создание не требуется.
  - `DJANGO_SUPERUSER_PHONE` — обязателен, так как телефон для пользователей уникальный и
    не может быть пустым.
  - `MINIO_ROOT_*` и `DOCUMENTS_STORAGE_*` — параметры доступа к локальному MinIO (docker).
  - `DOCUMENTS_ALLOWED_CONTENT_TYPES`, `DOCUMENTS_MAX_FILE_SIZE` — опциональные ограничения
    на типы и размер загружаемых файлов.

### MinIO для хранения документов
- Скопируйте `.env.example` в `.env`, при необходимости отредактируйте значения `MINIO_ROOT_*` и `DOCUMENTS_STORAGE_*`.
- Запустите MinIO локально: `docker compose --env-file .env -f docker/docker-compose.minio.yml up -d`.
- Консоль управления будет доступна на http://localhost:9001 (логин/пароль из `.env`).
- По умолчанию создаётся bucket `documents`; при необходимости измените `MINIO_BUCKET` и
  соответствующие переменные `DOCUMENTS_STORAGE_*`.

## Запуск приложения
- Создайте виртуальное окружение: `python3.11 -m venv venv`.
- Активируйте окружение: `source venv/bin/activate`.
- Установите зависимости (пока список формируется): `pip install -r backend/requirements.txt`.
- Примените миграции: `python backend/manage.py migrate` (добавлена миграция `applications.0002_schema_sync`).
- Заполните базу тестовыми данными при необходимости и запустите сервер: `python backend/manage.py runserver`.

## Проверка и вспомогательные команды
- `python backend/manage.py check` — быстрый smoke-тест конфигурации
- `python backend/manage.py spectacular --file backend/docs/openapi.yml` — регенерация схемы API
- `python backend/manage.py test` — полный тестовый прогон (пустой, но хук на будущее)
- `ruff check backend` / `ruff format backend` — линтер и форматтер

## Стиль кода
- Следуйте PEP 8 и внутренним правилам для именования.
- Пишите докстринги для модулей, классов и функций на русском языке.
- Не забывайте фиксировать зависимости, если что-то добавили туда.

## Статический анализ
- Запустите `ruff check backend` перед коммитом, чтобы найти проблемы стиля или импорта; для автоисправления добавьте `--fix`.
- Для форматирования воспользуйтесь `ruff format backend`.

## Документация API
- Схема доступна по `/api/schema/`, Swagger UI — `/api/docs/`, Redoc — `/api/redoc/`.
- Актуальная спецификация хранится в `backend/docs/openapi.yml`; для обновления выполните `python backend/manage.py spectacular --file backend/docs/openapi.yml`.
