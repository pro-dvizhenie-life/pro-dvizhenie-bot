
from django.core.management.base import BaseCommand

from applications.fixtures.applications import run, DEFAULT_REQUIREMENTS


class Command(BaseCommand):
    help = "Loads fixtures for applications."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Базовый URL API")
        parser.add_argument("--survey-code", default="default", help="Код формы (survey_code)")
        parser.add_argument("--count", type=int, default=30, help="Сколько заявок создать подряд")
        parser.add_argument("--verbose", action="store_true", help="Подробный лог")
        parser.add_argument(
            "--upload-files",
            action="store_true",
            help="Загружать случайные файлы из папки fixtures/documents",
        )
        parser.add_argument(
            "--requirements",
            default=",".join(DEFAULT_REQUIREMENTS),
            help="Список кодов требований через запятую.",
        )

    def handle(self, *args, **options):
        base_url = options["base_url"]
        survey_code = options["survey_code"]
        count = options["count"]
        verbose = options["verbose"]
        upload_files = options["upload_files"]
        requirements = [
            code.strip()
            for code in (options["requirements"].split(",") if options["requirements"] else [])
            if code.strip()
        ] or DEFAULT_REQUIREMENTS

        run(
            base_url=base_url,
            survey_code=survey_code,
            count=count,
            upload_files=upload_files,
            requirements=requirements,
            verbose=verbose,
        )
