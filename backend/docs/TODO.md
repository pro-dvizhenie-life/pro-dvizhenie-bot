# TODO

## Модели
- [ ] Users
  - [ ] Создать модель пользователя (кастомная, с менеджером)
  - [ ] Добавить роли (applicant, employee, admin)
  - [ ] Добавить платформенные поля (Telegram, Web)
  - [ ] Прописать AUTH_USER_MODEL в settings

- [ ] Applications
  - [x] Модель Application
  - [x] Модель Answer (динамические ответы вместо ApplicationData)
  - [ ] Модель ApplicationStatusHistory
  - [ ] Модель ApplicationComments
  - [x] Модели Survey/Step/Question/Option/Condition/DocumentRequirement
  - [x] Пройти чек-лист по моделям (verbose_name, __str__, ordering, related_name)

- [ ] Documents
  - [ ] Модель Document (тип, путь, статус)
  - [ ] Метаданные для ФЗ-152

- [ ] Consents
  - [ ] Модель DataConsent (тип, время, ip)

- [ ] Audit
  - [ ] Модель AuditLog (действие, таблица, ip, время)

## Админка
- [ ] Зарегистрировать Users c фильтрами по ролям
- [x] Зарегистрировать Applications c фильтрами по статусам и ответами
- [ ] Добавить инлайны для Documents и Comments
- [x] Настроить readonly поля и поиск для динамической анкеты

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
  - [x] POST /forms/<code>/sessions/ (создание сессии)
  - [x] GET черновика
  - [x] PATCH сохранение полей
  - [x] POST next шаг
  - [x] POST submit анкеты

## API
- [ ] Добавить роутер DRF
- [x] Настроить версионирование (/api/v1/)
- [ ] Подключить drf-spectacular для OpenAPI

## Документация
- [x] Обновить OpenAPI по динамической анкете
- [x] Подготовить Frontend Integration Guide

## Инфраструктура
- [ ] Перейти на PostgreSQL (docker-compose, settings)
- [ ] Настроить S3/MinIO (django-storages, boto3)
- [ ] Настроить docker-compose: db, redis, minio
