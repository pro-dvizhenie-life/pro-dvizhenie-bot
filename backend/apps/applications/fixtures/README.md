# Фикстуры анкет

## Загрузка данных
- `python backend/manage.py loaddata backend/apps/applications/fixtures/survey_default.json`
- `python backend/manage.py load_default_survey`

## Типы вопросов и формат ответов
- `text` — строка (обычно до 255 символов)
- `textarea` — многострочный текст
- `email` — строка в формате `user@example.com`
- `phone` — строка в формате `+7XXXXXXXXXX`
- `date` — дата `YYYY-MM-DD`
- `boolean` — булево значение `true`/`false`
- `select` — строка с кодом выбранного варианта
- `multiselect` — список строк с кодами вариантов
- `file` — идентификатор загруженного файла
- `file_multi` — список идентификаторов файлов

## JSON-логика условий
Условия описываются в формате [json-logic](https://jsonlogic.com/) с небольшими расширениями:
- `$q_code` — ссылка на ответ вопроса `q_code`
- Базовые операторы: `eq`, `neq`, `and`, `or`, `not`, `gt`, `gte`, `lt`, `lte`, `in`

Примеры:
- Показывать шаг взрослой ветки: `{"any":[{"eq":["$q_who_fills","self"]},{"eq":["$q_who_fills","relative"]}]}`
- Требовать документ для взрослого 14+: `{"and":[{"eq":["$branch","adult"]},{"gte":["$age",14]}]}`
- Видимость поля по чекбоксу: `{"eq":["$q_tsr_certificate_has", true]}`
