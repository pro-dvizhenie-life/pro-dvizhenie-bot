# TODO

Сейчас проект на SQlite. Предлагаю юзать его для простоты. Когда сделаем модели, тогда
предлагаю перейти на PostgreSQL.
Реализовал модель пользовователя, сделал автосоздание пользователя при первом запуске.
Добавляйте свои задачи сюда, если необходимо.

## Модели
- [ ] Users
  - [ ] Создать модель пользователя (кастомная, с менеджером)
  - [ ] Добавить роли (applicant, employee, admin)
  - [ ] Добавить платформенные поля (Telegram, Web)
  - [ ] Прописать AUTH_USER_MODEL в settings

- [ ] Applications
  - [ ] Модель Application
  - [ ] Модель ApplicationData (поля анкеты)
  - [ ] Модель ApplicationStatusHistory
  - [ ] Модель ApplicationComments

- [ ] Documents
  - [ ] Модель Document (тип, путь, статус)
  - [ ] Метаданные для ФЗ-152

- [ ] Consents
  - [ ] Модель DataConsent (тип, время, ip)

- [ ] Audit
  - [ ] Модель AuditLog (действие, таблица, ip, время)

## Админка
- [ ] Зарегистрировать Users c фильтрами по ролям
- [ ] Зарегистрировать Applications c фильтрами по статусам
- [ ] Добавить инлайны для Documents и Comments
- [ ] Настроить readonly поля и поиск

## Представления и URLs
- [ ] Users
  - [ ] /auth/login, logout, me
- [ ] Applications
  - [ ] /applications/ (list, detail)
  - [ ] /applications/{id}/status (смена статуса)
  - [ ] /applications/{id}/comments (CRUD комментариев)
- [ ] Documents
  - [ ] presigned upload
  - [ ] presigned download
- [ ] Consents
  - [ ] POST согласия
- [ ] Draft
  - [ ] GET черновика
  - [ ] PATCH сохранение полей
  - [ ] POST submit анкеты

## API
- [ ] Добавить роутер DRF
- [ ] Настроить версионирование (/api/v1/)
- [ ] Подключить drf-spectacular для OpenAPI

## Инфраструктура
- [ ] Перейти на PostgreSQL (docker-compose, settings)
- [ ] Настроить S3/MinIO (django-storages, boto3)
- [ ] Настроить docker-compose: db, redis, minio
