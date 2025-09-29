"""Пакет view-функций приложения заявок."""

from django.http import HttpResponse


def index(request):
    """Стартовая заглушка приложения заявок."""

    return HttpResponse("Applications index page")


__all__ = [
    "admin_views",
    "application_views",
    "export_views",
    "index",
]
