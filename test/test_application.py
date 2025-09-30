#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import mimetypes
import random
import string
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from uuid import uuid4

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_UPLOAD = SCRIPT_DIR / "image.jpg"
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


def gen_phone_ru() -> str:
    # формируем мобильный РФ формата +7XXXXXXXXXX, начинаем с "9" (как в примере API валидации)
    digits = "9" + "".join(random.choice(string.digits) for _ in range(9))
    return f"+7{digits}"

def gen_email() -> str:
    return f"{uuid4().hex[:10]}@example.net"

def submit_one(
    base_url: str,
    survey_code: str,
    *,
    upload_file: Optional[str] = None,
    requirements: Iterable[str] = DEFAULT_REQUIREMENTS,
    verbose: bool = False,
) -> dict:
    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    t0 = time.perf_counter()

    def url(path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"

    # 1) создать сессию анкеты (без авторизации)
    r = s.post(url(f"/api/v1/applications/forms/{survey_code}/sessions/"), json={})
    r.raise_for_status()
    public_id = r.json()["public_id"]
    if verbose:
        print("created session:", public_id)

    # 2) заполнить интро (s0_intro): согласие и кто заполняет
    r = s.patch(
        url(f"/api/v1/applications/{public_id}/draft/patch/"),
        json={"answers": [
            {"question_code": "q_agree", "value": True},
            {"question_code": "q_who_fills", "value": "self"},
        ]},
    )
    r.raise_for_status()
    if verbose:
        print("patched s0_intro OK")

    # 3) перейти на s1_basic
    r = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={})
    r.raise_for_status()
    if verbose:
        print("moved to s1_basic")

    # 4) заполнить s1_basic (генерируем телефон и email)
    phone = gen_phone_ru()
    email = gen_email()
    r = s.patch(
        url(f"/api/v1/applications/{public_id}/draft/patch/"),
        json={"answers": [
            {"question_code": "q_fullname",    "value": "Иванов Иван Иванович"},
            {"question_code": "q_dob",         "value": "2015-06-15"},
            {"question_code": "q_city",        "value": "Тбилиси"},
            {"question_code": "q_phone",       "value": phone},
            {"question_code": "q_email",       "value": email},
            {"question_code": "q_what_to_buy", "value": "wheelchair"},
        ]},
    )
    r.raise_for_status()
    if verbose:
        print("patched s1_basic OK:", phone, email)

    # 5) перейти на s2_story_adult
    r = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={})
    r.raise_for_status()
    if verbose:
        print("moved to s2_story_adult")

    # 6) заполнить s2_story_adult (минимально обязательные поля)
    r = s.patch(
        url(f"/api/v1/applications/{public_id}/draft/patch/"),
        json={"answers": [
            {"question_code": "q_diagnosis_main",  "value": "ДЦП, спастическая диплегия"},
            {"question_code": "q_health_state",    "value": "Ограничена самостоятельная ходьба на длинные дистанции, требуется коляска."},
            {"question_code": "q_diagnosis_when",  "value": "Диагноз установлен в 2017 году"},
            {"question_code": "q_reason_need_tsr", "value": "Текущая коляска мала, вызывает дискомфорт. Нужна новая с поддержкой спины."},
        ]},
    )
    r.raise_for_status()
    if verbose:
        print("patched s2_story_adult OK")

    # 7) перейти на s3_docs
    r = s.post(url(f"/api/v1/applications/{public_id}/next/"), json={})
    r.raise_for_status()
    if verbose:
        print("moved to s3_docs")

    uploaded_docs: List[Dict[str, str]] = []
    if upload_file:
        for req_code in requirements:
            uploaded_docs.append(
                upload_document(
                    session=s,
                    url_builder=url,
                    application_id=public_id,
                    requirement_code=req_code,
                    file_path=upload_file,
                    verbose=verbose,
                )
            )

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


def main():
    ap = argparse.ArgumentParser(description="Гонщик анкет Pro Dvizhenie")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="Базовый URL API")
    ap.add_argument("--survey-code", default="default", help="Код формы (survey_code)")
    ap.add_argument("--count", type=int, default=1, help="Сколько заявок создать подряд")
    ap.add_argument("--verbose", action="store_true", help="Подробный лог")
    ap.add_argument(
        "--upload-file",
        default=str(DEFAULT_UPLOAD),
        help="Путь к файлу, который загрузится на шаге документов (оставьте пустым, чтобы пропустить)",
    )
    ap.add_argument(
        "--requirements",
        default=",".join(DEFAULT_REQUIREMENTS),
        help=(
            "Список кодов требований через запятую. Одновременно загрузится один и тот же файл"
            " для каждого кода."
        ),
    )
    ap.add_argument(
        "--skip-upload",
        action="store_true",
        help="Не загружать файл даже при указании пути",
    )
    args = ap.parse_args()

    ok, fail = 0, 0
    for i in range(1, args.count + 1):
        try:
            upload_path = None if args.skip_upload else args.upload_file
            requirements = [
                code.strip()
                for code in (args.requirements.split(",") if args.requirements else [])
                if code.strip()
            ] or DEFAULT_REQUIREMENTS
            res = submit_one(
                args.base_url,
                args.survey_code,
                upload_file=upload_path if upload_path else None,
                requirements=requirements,
                verbose=args.verbose,
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
                f"[{i}/{args.count}] OK {res['public_id']} status={res['status']} t={res['seconds']}s"
                f" phone={res['phone']} email={res['email']}{doc_info}"
            )
        except requests.HTTPError as e:
            fail += 1
            r = e.response
            print(f"[{i}/{args.count}] FAIL HTTP {r.status_code} at {r.request.method} {r.request.url}")
            try:
                print("Body:", r.json())
            except Exception:
                print("Body:", r.text[:500])
        except Exception as e:
            fail += 1
            print(f"[{i}/{args.count}] FAIL {type(e).__name__}: {e}")

    print(f"\nDone. success={ok}, fail={fail}")

if __name__ == "__main__":
    main()
