# Начало

Запусти создание сессии для анкеты default и сразу сохрани куки:
```bash
curl -i -c cookies.txt -X POST 'http://localhost:8000/api/v1/applications/forms/default/sessions/' \
  -H 'Content-Type: application/json' -d '{}'
```

По OpenAPI этот эндпоинт допускает анонимный вызов (есть и `jwtAuth`, и пустая `security`) и на 201 вернёт объект `DraftOut` с `public_id`, `current_stage`, `current_step`. Этот `public_id` нам понадобится дальше.

## Сохраним PUBLIC_ID в переменную:

```bash
PUBLIC_ID="ваш-полученный-public_id-из-ответа-на-сессию"
```

**Важно:** Замените `"ваш-полученный-public_id-из-ответа-на-сессию"` на актуальный `public_id`, полученный в ответе от `/sessions/`.

Проверить:
```bash
echo $PUBLIC_ID
```

Куки сохранились в файл `cookies.txt`. Проверить:
```bash
cat cookies.txt
```

## Дальше

Теперь все запросы пишем с этими переменными. Обратите внимание, что заголовок `Cookie` с `session_token` вручную добавлять не обязательно, если вы используете флаг `-b cookies.txt` — curl сам подставит нужную куку из файла.

Пример запроса с флагом `-b`:

**ШАГ 1: s0_intro**

В ответе на `/sessions/` вы получили `current_step` с `code: "s0_intro"` и список вопросов. Используйте правильные `question_code` из этого ответа.

```bash
curl -i -b cookies.txt -X POST "http://localhost:8000/api/v1/applications/$PUBLIC_ID/next/" \
  -H "Content-Type: application/json" \
  -d '{
    "step_code": "s0_intro",
    "answers": [
      {"question_code": "q_agree", "value": true},
      {"question_code": "q_who_fills", "value": "self"}
    ]
  }'
```

**ВАЖНО:** В ответе на этот запрос (`/next/`) вы получите **новый** `current_step` и **новый** список `questions`. Обязательно используйте `code` этого *нового* шага в следующем вызове `/next/`, и `question_code` из *нового* списка вопросов.

### 2. Заполним основные данные (шаг `s1_basic`)

После шага `s0_intro` обычно идёт `s1_basic`. Используем правильные `question_code` из ответа сервера на предыдущий шаг.

```bash
curl -i -b cookies.txt -X POST "http://localhost:8000/api/v1/applications/$PUBLIC_ID/next/" \
  -H "Content-Type: application/json" \
  -d '{
    "step_code": "s1_basic",
    "answers": [
      {"question_code": "q_contact_name", "value": "Иванов Иван Иванович"},
      {"question_code": "q_fullname", "value": "Иванов Петр Иванович"},
      {"question_code": "q_dob", "value": "2000-01-01"},
      {"question_code": "q_city", "value": "Москва"},
      {"question_code": "q_phone", "value": "+79991234567"},
      {"question_code": "q_email", "value": "ivanov@example.com"},
      {"question_code": "q_what_to_buy", "value": "parts"},
      {"question_code": "q_tsr_certificate_has", "value": false},
      {"question_code": "q_other_funds_active", "value": false},
      {"question_code": "q_need_consulting", "value": []},
      {"question_code": "q_promo_capability", "value": false},
      {"question_code": "q_positioning_tips", "value": false},
      {"question_code": "q_esign_ready", "value": false}
    ]
  }'
```

### 3. Заполним историю подопечного (взрослый) (шаг `s2_story_adult`)

После `s1_basic`, если `q_who_fills` был `self` или `relative`, обычно идёт `s2_story_adult`. Используем правильные `question_code` из ответа сервера на предыдущий шаг.

```bash
curl -i -b cookies.txt -X POST "http://localhost:8000/api/v1/applications/$PUBLIC_ID/next/" \
  -H "Content-Type: application/json" \
  -d '{
    "step_code": "s2_story_adult",
    "answers": [
      {"question_code": "q_diagnosis_main", "value": "ДЦП"},
      {"question_code": "q_health_state", "value": "Ограничена самостоятельная ходьба на длинные дистанции."},
      {"question_code": "q_diagnosis_when", "value": "В 2 года"},
      {"question_code": "q_tsrs_in_ipra", "value": true},
      {"question_code": "q_deadline_need", "value": "2026-01-01"},
      {"question_code": "q_family_info", "value": "Небольшая семья. Родители поддерживают."},
      {"question_code": "q_motivation", "value": "Семья и друзья."},
      {"question_code": "q_hobby", "value": "Программирование."},
      {"question_code": "q_achievements", "value": "Окончил колледж."},
      {"question_code": "q_reason_need_tsr", "value": "Для большей независимости."},
      {"question_code": "q_message_to_readers", "value": "Спасибо за поддержку!"},
      {"question_code": "q_difficulties_ipra_mse", "value": "Трудности с получением."},
      {"question_code": "q_difficulties_stage", "value": "clinic"},
      {"question_code": "q_can_record_videos", "value": false},
      {"question_code": "q_additional_message", "value": "Дополнительное сообщение."}
    ]
  }'
```

### 4. Загрузим документы (шаг `s3_docs`)

После `s2_story_adult` (или `s2_story_child`) обычно идёт `s3_docs`. Используем правильные `question_code` из ответа сервера на предыдущий шаг. Для типов файлов используем `[]` как пустой массив или `null`, так как фактическая загрузка файлов требует отдельного шага с `presigned URL`.

```bash
curl -i -b cookies.txt -X POST "http://localhost:8000/api/v1/applications/$PUBLIC_ID/next/" \
  -H "Content-Type: application/json" \
  -d '{
    "step_code": "s3_docs",
    "answers": [
      {"question_code": "q_gosuslugi_confirmed", "value": false},
      {"question_code": "q_doc_birth_cert", "value": []},
      {"question_code": "q_doc_parent_passport", "value": []},
      {"question_code": "q_doc_beneficiary_passport", "value": []},
      {"question_code": "q_doc_ipra", "value": []},
      {"question_code": "q_doc_medical_report", "value": []},
      {"question_code": "q_doc_disability_cert", "value": []},
      {"question_code": "q_doc_snils", "value": []},
      {"question_code": "q_doc_photos_multi", "value": []}
    ]
  }'
```

### 5. Продолжаем заполнять анкету

Повторяйте шаг `curl ... /next/`, каждый раз:
*   Используя `code` *нового* `current_step` из предыдущего ответа в поле `step_code` тела запроса.
*   Используя правильные `question_code` из списка `questions` *нового* `current_step` в массиве `answers`.

### 6. Отправим заявку

Когда `current_step` в ответе на `/next/` станет `null` или `finished` (или вы решите, что всё заполнено), выполните финальную отправку:

```bash
curl -i -b cookies.txt -X POST "http://localhost:8000/api/v1/applications/$PUBLIC_ID/submit/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Завершение

Все шаги анкеты пройдены, заявка отправлена.

## Важное замечание

При выполнении запросов к эндпоинтам, требующим сессии (например, `/next/`, `/draft/`), **не** добавляйте заголовок `Cookie: session_token=$PUBLIC_ID` вручную, если используете `-b cookies.txt`. Куки из файла `cookies.txt` будут добавлены автоматически. Ручное добавление `Cookie` может привести к ошибке `401 Unauthorized`, так как сервер не сможет корректно аутентифицировать сессию.

**Проверяйте `question_code` и `step_code` в каждом ответе сервера перед формированием следующего запроса.**