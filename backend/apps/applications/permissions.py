"""Пользовательские разрешения для доступа к заявкам."""

from django.contrib.auth import get_user_model
from rest_framework import permissions

from .models import Application


class IsEmployeeOrAdmin(permissions.BasePermission):
    """Разрешение для сотрудников НКО и администраторов."""

    def has_permission(self, request, view):
        """Возвращает True, если пользователь аутентифицирован и имеет нужную роль."""

        User = get_user_model()
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in [User.Role.EMPLOYEE, User.Role.ADMIN]
        )


class IsOwner(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем проверяемой заявки."""

    def has_object_permission(self, request, view, obj):
        """Возвращает True только для владельца объекта Application."""

        if not isinstance(obj, Application):
            return False
        return obj.user == request.user


class IsOwnerOrEmployee(permissions.BasePermission):
    """Комбинированное разрешение для владельцев заявок и сотрудников."""

    def has_permission(self, request, view):
        """Разрешает доступ только аутентифицированным пользователям."""

        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Проверяет владение заявкой или наличие прав сотрудника/админа."""

        if not request.user or not request.user.is_authenticated:
            return False

        User = get_user_model()
        if request.user.role in [User.Role.EMPLOYEE, User.Role.ADMIN]:
            return True

        if isinstance(obj, Application):
            return obj.user == request.user

        return False
