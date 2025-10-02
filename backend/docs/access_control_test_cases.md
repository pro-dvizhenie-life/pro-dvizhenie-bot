# Тест-кейсы для проверки разграничения доступов

Этот документ описывает набор тест-кейсов для проверки корректной работы системы разграничения доступов после проведенного рефакторинга.

### Участники (Роли)

*   **Анонимный пользователь:** Неаутентифицированный пользователь.
*   **Заявитель (APPLICANT):** Аутентифицированный пользователь с ролью `APPLICANT`.
*   **Сотрудник (EMPLOYEE):** Аутентифицированный пользователь с ролью `EMPLOYEE`.
*   **Администратор (ADMIN):** Аутентифицированный пользователь с ролью `ADMIN`.

---

### 1. Анонимный пользователь

| ID | Описание | Ожидаемый результат |
|---|---|---|
| 1.1 | Попытка получить список заявок (`/api/v1/applications/`) | Ошибка 401 Unauthorized (или 403 Forbidden) |
| 1.2 | Попытка получить детали чужой заявки (`/api/v1/applications/{public_id}/`) | Ошибка 401 Unauthorized (или 403 Forbidden) |
| 1.3 | Попытка создать новую заявку (`/api/v1/surveys/{survey_code}/create_session/`) | Успешно (статус 201), в cookie устанавливается `session_token` |
| 1.4 | Попытка изменить статус заявки (`/api/v1/admin/applications/{public_id}/status/`) | Ошибка 401 Unauthorized (или 403 Forbidden) |

---

### 2. Заявитель (APPLICANT)

**Предусловия:**
*   Существует пользователь `applicant_A` с ролью `APPLICANT`, владеющий заявкой `application_A`.
*   Существует пользователь `applicant_B` с ролью `APPLICANT`, владеющий заявкой `application_B`.

| ID | Описание | Ожидаемый результат |
|---|---|---|
| 2.1 | `applicant_A` запрашивает список заявок (`/api/v1/applications/`) | Успешно (статус 200). В списке содержится только `application_A`, `application_B` отсутствует. |
| 2.2 | `applicant_A` запрашивает детали своей заявки `application_A` (`/api/v1/applications/{public_id_A}/`) | Успешно (статус 200). |
| 2.3 | `applicant_A` запрашивает детали чужой заявки `application_B` (`/api/v1/applications/{public_id_B}/`) | Ошибка 403 Forbidden. |
| 2.4 | `applicant_A` изменяет данные в своей заявке `application_A` (PATCH `/api/v1/applications/{public_id_A}/`) | Успешно (статус 200). |
| 2.5 | `applicant_A` пытается изменить данные в чужой заявке `application_B` (PATCH `/api/v1/applications/{public_id_B}/`) | Ошибка 403 Forbidden. |
| 2.6 | `applicant_A` пытается изменить статус своей заявки через админский эндпоинт (`/api/v1/admin/applications/{public_id_A}/status/`) | Ошибка 403 Forbidden. |
| 2.7 | `applicant_A` пытается получить детали своей заявки через админский эндпоинт (`/api/v1/admin/applications/{public_id_A}/`) | Ошибка 403 Forbidden. |
| 2.8 | `applicant_A` пытается добавить комментарий к своей заявке `application_A` | Ошибка 403 Forbidden. |
| 2.9 | `applicant_A` пытается добавить комментарий к чужой заявке `application_B` | Ошибка 403 Forbidden. |

---

### 3. Сотрудник (EMPLOYEE)

**Предусловия:**
*   Существует пользователь `employee` с ролью `EMPLOYEE`.
*   Существуют заявки `application_A` и `application_B` от разных заявителей.

| ID | Описание | Ожидаемый результат |
|---|---|---|
| 3.1 | `employee` запрашивает список заявок (`/api/v1/applications/`) | Успешно (статус 200). В списке содержатся обе заявки: `application_A` и `application_B`. |
| 3.2 | `employee` запрашивает детали заявки `application_A` (`/api/v1/applications/{public_id_A}/`) | Успешно (статус 200). |
| 3.3 | `employee` запрашивает детали заявки `application_A` через админский эндпоинт (`/api/v1/admin/applications/{public_id_A}/`) | Успешно (статус 200). |
| 3.4 | `employee` изменяет статус заявки `application_A` через админский эндпоинт (`/api/v1/admin/applications/{public_id_A}/status/`) | Успешно (статус 200). |
| 3.5 | `employee` добавляет комментарий к заявке `application_A` | Успешно (статус 201). |
| 3.6 | `employee` выполняет экспорт заявок в CSV (`/api/v1/export/csv/`) | Успешно (статус 200), получает файл. |

---

### 4. Администратор (ADMIN)

**Предусловия:**
*   Существует пользователь `admin` с ролью `ADMIN`.

| ID | Описание | Ожидаемый результат |
|---|---|---|
| 4.1 | `admin` запрашивает список заявок (`/api/v1/applications/`) | Успешно (статус 200). В списке содержатся все заявки. |
| 4.2 | `admin` запрашивает детали любой заявки через админский эндпоинт (`/api/v1/admin/applications/{public_id}/`) | Успешно (статус 200). |
| 4.3 | `admin` изменяет статус любой заявки (`/api/v1/admin/applications/{public_id}/status/`) | Успешно (статус 200). |
| 4.4 | `admin` выполняет экспорт заявок в CSV (`/api/v1/export/csv/`) | Успешно (статус 200), получает файл. |

