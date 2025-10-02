
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import calendar
import mimetypes
import random
import string
import time
from datetime import date, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

import requests

# --- Data for generation ---
FIRST_NAMES = ["Иван", "Петр", "Сергей", "Анна", "Мария", "Елена"]
LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Кузнецова", "Попова", "Смирнова"]
CITIES = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород"]
DIAGNOSES = ["ДЦП, спастическая диплегия", "Спинальная мышечная атрофия", "Аутизм", "Синдром Дауна"]
HEALTH_STATES = [
    "Ограничена самостоятельная ходьба на длинные дистанции, требуется коляска.",
    "Требуется постоянный уход и специализированное оборудование.",
    "Нуждается в реабилитации и развивающих занятиях.",
]
REASONS_NEED_TSR = [
    "Текущая коляска мала, вызывает дискомфорт. Нужна новая с поддержкой спины.",
    "Необходимо специализированное кресло для правильной осанки.",
    "Требуются ходунки для развития навыков ходьбы.",
]
WHAT_TO_BUY = ["wheelchair", "addon", "parts"]

FEMALE_FIRST_NAMES = {"Анна", "Мария", "Елена"}
PATRONYMICS_BY_GENDER = {
    "male": ["Алексеевич", "Андреевич", "Владимирович", "Игоревич", "Сергеевич"],
    "female": ["Алексеевна", "Андреевна", "Владимировна", "Игоревна", "Сергеевна"],
}
CONSULTING_REQUESTS = [
    "Нужна помощь с подготовкой документов для МСЭ и обновлением ИПРА.",
    "Хотим уточнить порядок получения ТСР через СФР и перечень документов.",
    "Нужна консультация по составлению рекомендаций в ИПРА и сбору справок.",
]
OTHER_FUNDS_DETAILS = [
    "Уже идёт сбор в фонде \"Добро вместе\" на сумму 210 000 ₽ (ссылка: https://example.org/campaign/123).",
    "Запущена кампания на платформе Planeta.ru, собрано 45% цели.",
    "Часть средств собираем через фонд \"Лучшие друзья\", но не хватает на оборудование.",
]
FAMILY_INFO_TEXTS = [
    "Живём вместе с супругой и дочерью, помогают родственники и друзья.",
    "Семья состоит из мамы, бабушки и старшего брата, которые поддерживают ежедневно.",
    "Рядом живут родители и соседи, всегда готовы помочь по уходу.",
]
DEADLINE_TEXTS = [
    "Важно успеть до начала учебного года в сентябре.",
    "Оборудование нужно до очередного курса реабилитации в июне.",
    "Хотим подготовиться к соревнованиям, которые пройдут осенью.",
]
MOTIVATION_TEXTS = [
    "Вдохновляют успехи параспортсменов и поддержка семьи.",
    "Мотивирует желание оставаться активным и двигаться вперёд.",
    "Силы придают близкие люди и даже маленькие победы.",
]
HOBBY_TEXTS = [
    "Люблю прикладное творчество и рисование.",
    "Нравится заниматься адаптивным спортом и плаванием.",
    "Занимаюсь музыкой и изучаю гитару.",
]
ACHIEVEMENTS_TEXTS = [
    "Участие в городском марафоне и первые километры на коляске.",
    "Получена грамота за активную позицию и помощь другим подопечным.",
    "Удалось вернуться к работе после реабилитации.",
]
MESSAGES_TO_READERS = [
    "Спасибо за поддержку и внимание к нашей истории.",
    "Верим, что вместе сможем сделать шаг вперёд.",
    "Каждый отклик важен и придаёт сил двигаться дальше.",
]
ADDITIONAL_NOTES = [
    "Готов поделиться опытом с другими семьями, которые проходят похожий путь.",
    "Всегда рады обратной связи и советам специалистов.",
    "Готовы участвовать в мероприятиях фонда и рассказывать историю.",
]
DIFFICULTIES_TEXTS = [
    "Сталкивались с длительными сроками рассмотрения документов.",
    "Требовалось повторно собирать справки из разных учреждений.",
    "Сложно получить нужные рекомендации без дополнительной поддержки.",
]
TSR_IN_IPRA_TEXTS = [
    "ТСР включено в ИПРА с 2021 года, но финансирование задерживается.",
    "В ИПРА указано, что необходимо обновить коляску в этом году.",
]
CHILD_HEALTH_STATES = [
    "Ребёнку нужна поддержка при передвижении и регулярная реабилитация.",
    "Требуется специальное оборудование для занятий дома.",
    "Необходимы ТСР для самостоятельности и обучения.",
]
CHILD_FAMILY_INFO_TEXTS = [
    "Мама в декрете, папа работает удалённо, помогает бабушка.",
    "Семья большая: родители, старший брат и тётя всегда рядом.",
    "Живём вместе с бабушкой, она помогает с уходом и занятиями.",
]
CHILD_TRADITIONS_TEXTS = [
    "По выходным всей семьёй смотрим фильмы и обсуждаем планы.",
    "Каждое лето выезжаем на природу и устраиваем пикники.",
    "Любим вместе готовить и устраивать настольные игры по вечерам.",
]
CHILD_HOBBIES_TEXTS = [
    "Нравится лепить из глины и посещать арт-студию.",
    "Любит адаптивное плавание и занятия музыкой.",
    "Увлекается робототехникой и конструктором.",
]
CHILD_DREAMS_TEXTS = [
    "Мечтает поехать в инклюзивный лагерь летом.",
    "Хочет научиться играть на пианино и выступить на сцене.",
    "Мечтает самостоятельно передвигаться и посещать школу без барьеров.",
]
CHILD_MESSAGES_TEXTS = [
    "Спасибо за поддержку, мы очень ценим любое внимание.",
    "Вместе мы сможем подарить ребёнку больше свободы.",
    "Благодарим за заботу и возможность двигаться к мечте.",
]
CHILD_ADDITIONAL_NOTES = [
    "Готовы делиться историями прогресса и участвовать в мероприятиях.",
    "Рады знакомству с другими семьями и обмену опытом.",
]
APPLICANT_TYPES = ["self", "parent", "guardian", "relative"]


DEFAULT_REQUIREMENTS = [
    "birth_cert",
    "parent_passport",
    "beneficiary_passport",
    "ipra",
    "medical_report",
    "disability_cert",
    "snils",
    "photos_multi",
]

FIXTURE_DOCS_DIR = Path(__file__).resolve().parent / "documents"


def gen_phone_ru() -> str:
    # формируем мобильный РФ формата +7XXXXXXXXXX, начинаем с "9" (как в примере API валидации)
    digits = "9" + "".join(random.choice(string.digits) for _ in range(9))
    return f"+7{digits}"


def gen_email() -> str:
    return f"{uuid4().hex[:10]}@example.net"


def _random_date_between(start_year: int, end_year: int) -> date:
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def generate_fixture_data() -> Dict[str, Any]:
    """Generates structured answers that satisfy survey requirements."""

    applicant_type = random.choice(APPLICANT_TYPES)
    branch = "adult" if applicant_type in {"self", "relative"} else "child"

    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = "female" if first_name in FEMALE_FIRST_NAMES else "male"
    patronymic = random.choice(PATRONYMICS_BY_GENDER[gender])
    full_name = f"{last_name} {first_name} {patronymic}"

    dob_value = _random_date_between(1980, 2005) if branch == "adult" else _random_date_between(2011, 2020)
    city = random.choice(CITIES)
    phone = gen_phone_ru()
    email = gen_email()

    contact_name: Optional[str] = None
    if applicant_type != "self":
        contact_first = random.choice(FIRST_NAMES)
        contact_gender = "female" if contact_first in FEMALE_FIRST_NAMES else "male"
        contact_name = (
            f"{random.choice(LAST_NAMES)} {contact_first} "
            f"{random.choice(PATRONYMICS_BY_GENDER[contact_gender])}"
        )

    tsr_has = random.random() < 0.4
    cert_number = cert_amount = cert_valid_until = None
    if tsr_has:
        cert_number = f"CERT-{random.randint(100000, 999999)}"
        cert_amount = f"{random.randint(80, 240) * 1000} ₽"
        cert_valid_until = (date.today() + timedelta(days=random.randint(120, 720))).isoformat()

    other_funds_active = random.random() < 0.3
    other_funds_details = random.choice(OTHER_FUNDS_DETAILS) if other_funds_active else None
    need_consulting = random.choice(CONSULTING_REQUESTS) if random.random() < 0.5 else None
    promo_capability = random.random() < 0.6
    positioning_tips = random.random() < 0.75
    esign_ready = random.random() < 0.5

    adult_story = {
        "q_diagnosis_main": random.choice(DIAGNOSES),
        "q_health_state": random.choice(HEALTH_STATES),
        "q_diagnosis_when": f"Диагноз поставлен в {random.randint(2010, 2023)} году",
        "q_tsrs_in_ipra": random.choice(TSR_IN_IPRA_TEXTS) if random.random() < 0.65 else None,
        "q_deadline_need": random.choice(DEADLINE_TEXTS) if random.random() < 0.6 else None,
        "q_family_info": random.choice(FAMILY_INFO_TEXTS) if random.random() < 0.7 else None,
        "q_motivation": random.choice(MOTIVATION_TEXTS) if random.random() < 0.7 else None,
        "q_hobby": random.choice(HOBBY_TEXTS) if random.random() < 0.6 else None,
        "q_achievements": random.choice(ACHIEVEMENTS_TEXTS) if random.random() < 0.5 else None,
        "q_reason_need_tsr": random.choice(REASONS_NEED_TSR),
        "q_message_to_readers": random.choice(MESSAGES_TO_READERS) if random.random() < 0.6 else None,
        "q_difficulties_ipra_mse": random.choice(DIFFICULTIES_TEXTS) if random.random() < 0.5 else None,
        "q_difficulties_stage": random.choice(["clinic", "mse", "other", None]),
        "q_can_record_videos": random.random() < 0.65,
        "q_additional_message": random.choice(ADDITIONAL_NOTES) if random.random() < 0.4 else None,
    }

    child_deadline = (
        (date.today() + timedelta(days=random.randint(60, 240))).isoformat()
        if random.random() < 0.5
        else None
    )
    child_story = {
        "q_child_diagnosis_main": random.choice(DIAGNOSES),
        "q_child_health_state": random.choice(CHILD_HEALTH_STATES),
        "q_child_diagnosis_when": f"Диагноз подтверждён в {random.randint(2016, 2023)} году",
        "q_child_tsrs_in_ipra": random.random() < 0.6,
        "q_child_deadline_need": child_deadline,
        "q_parent_family_info": random.choice(CHILD_FAMILY_INFO_TEXTS) if random.random() < 0.7 else None,
        "q_child_family_traditions": random.choice(CHILD_TRADITIONS_TEXTS) if random.random() < 0.6 else None,
        "q_child_hobby": random.choice(CHILD_HOBBIES_TEXTS) if random.random() < 0.6 else None,
        "q_child_dream": random.choice(CHILD_DREAMS_TEXTS) if random.random() < 0.6 else None,
        "q_child_reason_need_tsr": random.choice(REASONS_NEED_TSR),
        "q_child_message_to_readers": random.choice(CHILD_MESSAGES_TEXTS) if random.random() < 0.6 else None,
        "q_child_difficulties_ipra_mse": random.choice(DIFFICULTIES_TEXTS) if random.random() < 0.5 else None,
        "q_child_difficulties_stage": random.choice(["clinic", "mse", "other", None]),
        "q_child_can_record_videos": random.random() < 0.6,
        "q_child_additional_message": random.choice(CHILD_ADDITIONAL_NOTES) if random.random() < 0.4 else None,
    }

    basic_data = {
        "q_contact_name": contact_name,
        "q_fullname": full_name,
        "q_dob": dob_value.isoformat(),
        "q_city": city,
        "q_phone": phone,
        "q_email": email,
        "q_what_to_buy": random.choice(WHAT_TO_BUY),
        "q_tsr_certificate_has": tsr_has,
        "q_tsr_cert_number": cert_number,
        "q_tsr_cert_amount": cert_amount,
        "q_tsr_cert_valid_until": cert_valid_until,
        "q_other_funds_active": other_funds_active,
        "q_other_funds_details": other_funds_details,
        "q_need_consulting": need_consulting,
        "q_promo_capability": promo_capability,
        "q_positioning_tips": positioning_tips,
        "q_esign_ready": esign_ready,
    }

    docs_data = {
        "q_gosuslugi_confirmed": random.random() < 0.35,
    }

    return {
        "applicant_type": applicant_type,
        "branch": branch,
        "phone": phone,
        "email": email,
        "basic": basic_data,
        "adult_story": adult_story,
        "child_story": child_story,
        "docs": docs_data,
    }


def append_answer(answers: List[Dict[str, Any]], code: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    answers.append({"question_code": code, "value": value})


def _extract_step_code(payload: Dict[str, Any]) -> Optional[str]:
    step = payload.get("current_step")
    if isinstance(step, dict):
        return step.get("code")
    return None


def submit_one(
    base_url: str,
    survey_code: str,
    data: Dict[str, Any],
    *,
    upload_files: bool = False,
    requirements: Iterable[str] = DEFAULT_REQUIREMENTS,
    verbose: bool = False,
) -> dict:
    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    t0 = time.perf_counter()

    def url(path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"

    phone = data["phone"]
    email = data["email"]

    session_payload = {"applicant_type": data["applicant_type"]}
    r = s.post(url(f"/api/v1/applications/forms/{survey_code}/sessions/"), json=session_payload)
    r.raise_for_status()
    public_id = r.json()["public_id"]
    if verbose:
        print("created session:", public_id, "type=", data["applicant_type"])

    intro_answers: List[Dict[str, Any]] = []
    append_answer(intro_answers, "q_agree", True)
    append_answer(intro_answers, "q_who_fills", data["applicant_type"])
    r = s.patch(url(f"/api/v1/applications/{public_id}/draft/patch/"), json={"answers": intro_answers})
    r.raise_for_status()

    next_payload = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={}).json()
    step_code = _extract_step_code(next_payload)
    if step_code != "s1_basic":
        raise RuntimeError(f"Unexpected step after intro: {step_code}")
    if verbose:
        print("moved to", step_code)

    basic = data["basic"]
    basic_answers: List[Dict[str, Any]] = []
    append_answer(basic_answers, "q_contact_name", basic.get("q_contact_name"))
    append_answer(basic_answers, "q_fullname", basic["q_fullname"])
    append_answer(basic_answers, "q_dob", basic["q_dob"])
    append_answer(basic_answers, "q_city", basic.get("q_city"))
    append_answer(basic_answers, "q_phone", phone)
    append_answer(basic_answers, "q_email", email)
    append_answer(basic_answers, "q_what_to_buy", basic["q_what_to_buy"])
    append_answer(basic_answers, "q_tsr_certificate_has", basic["q_tsr_certificate_has"])
    append_answer(basic_answers, "q_tsr_cert_number", basic.get("q_tsr_cert_number"))
    append_answer(basic_answers, "q_tsr_cert_amount", basic.get("q_tsr_cert_amount"))
    append_answer(basic_answers, "q_tsr_cert_valid_until", basic.get("q_tsr_cert_valid_until"))
    append_answer(basic_answers, "q_other_funds_active", basic["q_other_funds_active"])
    append_answer(basic_answers, "q_other_funds_details", basic.get("q_other_funds_details"))
    append_answer(basic_answers, "q_need_consulting", basic.get("q_need_consulting"))
    append_answer(basic_answers, "q_promo_capability", basic["q_promo_capability"])
    append_answer(basic_answers, "q_positioning_tips", basic["q_positioning_tips"])
    append_answer(basic_answers, "q_esign_ready", basic["q_esign_ready"])
    r = s.patch(url(f"/api/v1/applications/{public_id}/draft/patch/"), json={"answers": basic_answers})
    r.raise_for_status()
    if verbose:
        print("patched s1_basic OK")

    next_payload = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={}).json()
    story_step = _extract_step_code(next_payload)
    if story_step not in {"s2_story_adult", "s2_story_child"}:
        raise RuntimeError(f"Unexpected step after basics: {story_step}")
    if verbose:
        print("moved to", story_step)

    story_answers: List[Dict[str, Any]] = []
    if story_step == "s2_story_adult":
        story = data["adult_story"]
        append_answer(story_answers, "q_diagnosis_main", story["q_diagnosis_main"])
        append_answer(story_answers, "q_health_state", story["q_health_state"])
        append_answer(story_answers, "q_diagnosis_when", story["q_diagnosis_when"])
        append_answer(story_answers, "q_reason_need_tsr", story["q_reason_need_tsr"])
        append_answer(story_answers, "q_tsrs_in_ipra", story.get("q_tsrs_in_ipra"))
        append_answer(story_answers, "q_deadline_need", story.get("q_deadline_need"))
        append_answer(story_answers, "q_family_info", story.get("q_family_info"))
        append_answer(story_answers, "q_motivation", story.get("q_motivation"))
        append_answer(story_answers, "q_hobby", story.get("q_hobby"))
        append_answer(story_answers, "q_achievements", story.get("q_achievements"))
        append_answer(story_answers, "q_message_to_readers", story.get("q_message_to_readers"))
        append_answer(story_answers, "q_difficulties_ipra_mse", story.get("q_difficulties_ipra_mse"))
        append_answer(story_answers, "q_difficulties_stage", story.get("q_difficulties_stage"))
        append_answer(story_answers, "q_can_record_videos", story["q_can_record_videos"])
        append_answer(story_answers, "q_additional_message", story.get("q_additional_message"))
    else:
        story = data["child_story"]
        append_answer(story_answers, "q_child_diagnosis_main", story["q_child_diagnosis_main"])
        append_answer(story_answers, "q_child_health_state", story["q_child_health_state"])
        append_answer(story_answers, "q_child_diagnosis_when", story["q_child_diagnosis_when"])
        append_answer(story_answers, "q_child_reason_need_tsr", story["q_child_reason_need_tsr"])
        append_answer(story_answers, "q_child_tsrs_in_ipra", story["q_child_tsrs_in_ipra"])
        append_answer(story_answers, "q_child_deadline_need", story.get("q_child_deadline_need"))
        append_answer(story_answers, "q_parent_family_info", story.get("q_parent_family_info"))
        append_answer(story_answers, "q_child_family_traditions", story.get("q_child_family_traditions"))
        append_answer(story_answers, "q_child_hobby", story.get("q_child_hobby"))
        append_answer(story_answers, "q_child_dream", story.get("q_child_dream"))
        append_answer(story_answers, "q_child_message_to_readers", story.get("q_child_message_to_readers"))
        append_answer(story_answers, "q_child_difficulties_ipra_mse", story.get("q_child_difficulties_ipra_mse"))
        append_answer(story_answers, "q_child_difficulties_stage", story.get("q_child_difficulties_stage"))
        append_answer(story_answers, "q_child_can_record_videos", story["q_child_can_record_videos"])
        append_answer(story_answers, "q_child_additional_message", story.get("q_child_additional_message"))

    r = s.patch(url(f"/api/v1/applications/{public_id}/draft/patch/"), json={"answers": story_answers})
    r.raise_for_status()

    next_payload = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={}).json()
    docs_step = _extract_step_code(next_payload)
    if docs_step not in {"s3_docs", None}:
        raise RuntimeError(f"Unexpected docs step: {docs_step}")
    if verbose:
        print("moved to", docs_step or "final step")

    docs_answers: List[Dict[str, Any]] = []
    docs = data["docs"]
    append_answer(docs_answers, "q_gosuslugi_confirmed", docs.get("q_gosuslugi_confirmed"))
    if docs_answers:
        r = s.patch(url(f"/api/v1/applications/{public_id}/draft/patch/"), json={"answers": docs_answers})
        r.raise_for_status()

    uploaded_docs: List[Dict[str, str]] = []
    document_paths = [
        p
        for p in FIXTURE_DOCS_DIR.iterdir()
        if p.is_file() and not p.name.startswith(".")
    ] if FIXTURE_DOCS_DIR.exists() else []

    temp_path: Optional[Path] = None
    if not document_paths:
        tmp = NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(b"Fixture document generated automatically.\n")
        tmp.flush()
        tmp.close()
        temp_path = Path(tmp.name)
        document_paths = [temp_path]

    for req_code in requirements:
        upload_path = str(random.choice(document_paths))
        uploaded_docs.append(
            upload_document(
                session=s,
                url_builder=url,
                application_id=public_id,
                requirement_code=req_code,
                file_path=upload_path,
                verbose=verbose,
            )
        )

    if temp_path:
        temp_path.unlink(missing_ok=True)

    # 8) отправить заявку
    r = s.post(url(f"/api/v1/applications/{public_id}/submit/"), json={})
    r.raise_for_status()
    status = r.json().get("status", "")

    dt = time.perf_counter() - t0
    result = {
        "public_id": public_id,
        "phone": phone,
        "email": email,
        "status": status,
        "seconds": round(dt, 3),
        "applicant_type": data["applicant_type"],
        "branch": data["branch"],
    }
    if uploaded_docs:
        result["documents"] = uploaded_docs
    if verbose:
        print("submitted:", result)
    return result


def upload_document(
    *,
    session: requests.Session,
    url_builder: Callable[[str], str],
    application_id: str,
    requirement_code: str,
    file_path: str,
    verbose: bool,
) -> Dict[str, str]:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Файл для загрузки не найден: {file_path}")

    filename = path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    size = path.stat().st_size

    payload = {
        "application_id": application_id,
        "requirement_code": requirement_code,
        "filename": filename,
        "content_type": content_type,
        "size": size,
    }
    r = session.post(url_builder("/api/v1/documents/uploads/"), json=payload)
    r.raise_for_status()
    payload = r.json()
    upload = payload["upload"]

    fields = {key: str(value) for key, value in (upload.get("fields") or {}).items()}

    with path.open("rb") as fp:
        files = {"file": (filename, fp, content_type)}
        headers = upload.get("headers") or {}
        post_resp = requests.post(upload["url"], data=fields, files=files, headers=headers)
        post_resp.raise_for_status()
        etag = post_resp.headers.get("ETag")

    complete_payload: Dict[str, str] = {}
    if etag:
        complete_payload["etag"] = etag.strip('"')
    r = session.post(
        url_builder(f"/api/v1/documents/uploads/{payload['version_id']}/complete/"),
        json=complete_payload,
    )
    r.raise_for_status()

    result = {
        "requirement_code": requirement_code,
        "document_id": payload["document_id"],
        "version_id": payload["version_id"],
    }

    if verbose:
        print(
            "uploaded document:",
            {
                **result,
                "filename": filename,
                "content_type": content_type,
                "size": size,
            },
        )

    return result


def run(*, base_url: str, survey_code: str, count: int, upload_files: bool, requirements: List[str], verbose: bool):
    ok, fail = 0, 0
    for i in range(1, count + 1):
        try:
            data = generate_fixture_data()
            res = submit_one(
                base_url,
                survey_code,
                data,
                upload_files=upload_files,
                requirements=requirements,
                verbose=verbose,
            )
            ok += 1
            doc_info = ""
            if "documents" in res:
                doc_pairs = [
                    f"{doc['requirement_code']}={doc['document_id']}:{doc['version_id']}"
                    for doc in res["documents"]
                ]
                doc_info = f" documents={'|'.join(doc_pairs)}"
            print(
                f"[{i}/{count}] OK {res['public_id']} status={res['status']} t={res['seconds']}s "
                f"type={res['applicant_type']} branch={res['branch']} "
                f"phone={res['phone']} email={res['email']}{doc_info}"
            )
        except requests.HTTPError as e:
            fail += 1
            r = e.response
            print(f"[{i}/{count}] FAIL HTTP {r.status_code} at {r.request.method} {r.request.url}")
            try:
                print("Body:", r.json())
            except Exception:
                print("Body:", r.text[:500])
        except Exception as e:
            fail += 1
            print(f"[{i}/{count}] FAIL {type(e).__name__}: {e}")

    print(f"\nDone. success={ok}, fail={fail}")
