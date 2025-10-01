"""Пользовательские фильтры для шаблонов админки заявок."""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def get_item(bound_field_container, key):
    """Безопасно возвращает BoundField по имени."""

    if not key or bound_field_container is None:
        return None
    try:
        return bound_field_container[key]
    except Exception:  # pragma: no cover - защита от неверных ключей
        return None

