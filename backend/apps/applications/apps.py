"""Конфигурация приложения заявок с автоинициализацией сигналов."""

from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications'
    verbose_name = 'Анкеты и заявки'

    def ready(self) -> None:  # pragma: no cover - вызывается Django
        super().ready()
        from . import signals  # noqa: F401 импортирует обработчики post_migrate
