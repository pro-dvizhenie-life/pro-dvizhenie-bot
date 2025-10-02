"""Модели и менеджеры пользователей."""

from __future__ import annotations

import hashlib

from config.constants import (
    MAGIC_LINK_TOKEN_HASH_LENGTH,
    USER_CHOICE_MAX_LENGTH,
    USER_EMAIL_MAX_LENGTH,
    USER_PHONE_MAX_LENGTH,
    USER_SESSION_TOKEN_MAX_LENGTH,
    USER_TELEGRAM_USERNAME_MAX_LENGTH,
)
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Кастомный менеджер для модели User."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """Создаёт и сохраняет пользователя с переданными данными."""

        if not email:
            raise ValueError('Необходимо указать адрес электронной почты.')
        phone = extra_fields.get('phone')
        if not phone:
            raise ValueError('Необходимо указать номер телефона.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields
    ):
        """Создаёт обычного пользователя без прав администратора."""

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.APPLICANT)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields
    ):
        """Создаёт суперпользователя с обязательными флагами доступа."""

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(
                'Суперпользователь должен иметь is_superuser=True.'
            )

        if not password:
            raise ValueError('Суперпользователь обязан иметь пароль.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Кастомная модель пользователя."""

    class Role(models.TextChoices):
        """Роли пользователей."""
        APPLICANT = 'applicant', 'Заявитель'
        EMPLOYEE = 'employee', 'Сотрудник'
        ADMIN = 'admin', 'Администратор'

    class Platform(models.TextChoices):
        """Платформы, с которых пользователь может взаимодействовать
        с системой."""
        WEB = 'web', 'Веб-интерфейс'
        TELEGRAM = 'telegram', 'Телеграм'

    id = models.AutoField(
        verbose_name='Идентификатор',
        primary_key=True,
        editable=False,
    )
    email = models.EmailField(
        verbose_name='Электронная почта',
        max_length=USER_EMAIL_MAX_LENGTH,
        unique=True,
    )
    phone = models.CharField(
        verbose_name='Номер телефона',
        max_length=USER_PHONE_MAX_LENGTH,
        unique=True,
    )
    role = models.CharField(
        verbose_name='Роль',
        max_length=USER_CHOICE_MAX_LENGTH,
        choices=Role.choices,
        default=Role.APPLICANT,
    )
    telegram_chat_id = models.BigIntegerField(
        verbose_name='Идентификатор чата в Telegram',
        null=True,
        blank=True,
        unique=True,
    )
    telegram_username = models.CharField(
        verbose_name='Имя пользователя в Telegram',
        max_length=USER_TELEGRAM_USERNAME_MAX_LENGTH,
        null=True,
        blank=True,
    )
    website_session_token = models.CharField(
        verbose_name='Токен сессии на сайте',
        max_length=USER_SESSION_TOKEN_MAX_LENGTH,
        null=True,
        blank=True,
        unique=True,
    )
    primary_platform = models.CharField(
        verbose_name='Основная платформа',
        max_length=USER_CHOICE_MAX_LENGTH,
        choices=Platform.choices,
        null=True,
        blank=True,
    )
    last_platform_used = models.CharField(
        verbose_name='Последняя используемая платформа',
        max_length=USER_CHOICE_MAX_LENGTH,
        choices=Platform.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
    )
    last_telegram_activity = models.DateTimeField(
        verbose_name='Последняя активность в Telegram',
        null=True,
        blank=True,
    )
    last_website_activity = models.DateTimeField(
        verbose_name='Последняя активность на сайте',
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
    )
    is_staff = models.BooleanField(
        verbose_name='Сотрудник',
        default=False,
    )

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = ['phone']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('-created_at',)

    def __str__(self) -> str:
        """Возвращает читаемое представление пользователя."""

        return self.email

    def get_full_name(self) -> str:
        """Возвращает полное имя пользователя для административных нужд."""

        return self.email

    def get_short_name(self) -> str:
        """Возвращает краткое отображаемое имя пользователя."""

        return self.email


class MagicLinkTokenQuerySet(models.QuerySet):
    """Дополнительные методы работы с токенами магической ссылки."""

    def active(self):
        """Фильтрует только неиспользованные и неистёкшие токены."""

        now = timezone.now()
        return self.filter(used_at__isnull=True, expires_at__gt=now)


class MagicLinkTokenManager(models.Manager):
    """Менеджер токенов входа по magic link."""

    def get_queryset(self):
        """Возвращает базовый queryset с пользовательским API."""

        return MagicLinkTokenQuerySet(self.model, using=self._db)

    def verify(self, raw_token: str) -> "MagicLinkToken | None":
        """Возвращает токен, если он существует и действителен."""

        if not raw_token:
            return None
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            token = (
                self.get_queryset()
                .select_related("user")
                .get(token_hash=token_hash)
            )
        except MagicLinkToken.DoesNotExist:
            return None
        if token.used_at is not None:
            return None
        if token.expires_at <= timezone.now():
            return None
        return token


class MagicLinkToken(models.Model):
    """Одноразовые токены для входа пользователя по email-ссылке."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="magic_link_tokens",
        verbose_name="Пользователь",
    )
    token_hash = models.CharField(
        verbose_name="Хеш токена",
        max_length=MAGIC_LINK_TOKEN_HASH_LENGTH,
        unique=True,
    )
    created_at = models.DateTimeField(
        verbose_name="Создан",
        auto_now_add=True,
    )
    expires_at = models.DateTimeField(
        verbose_name="Истекает",
    )
    used_at = models.DateTimeField(
        verbose_name="Использован",
        null=True,
        blank=True,
    )
    last_ip = models.GenericIPAddressField(
        verbose_name="IP при использовании",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        verbose_name="User-Agent",
        null=True,
        blank=True,
    )

    objects = MagicLinkTokenManager()

    class Meta:
        verbose_name = "Токен входа по ссылке"
        verbose_name_plural = "Токены входа по ссылке"
        ordering = ("-created_at",)

    def mark_used(self, *, ip: str | None = None, user_agent: str | None = None) -> None:
        """Помечает токен использованным и сохраняет метаданные."""

        self.used_at = timezone.now()
        update_fields = ["used_at"]
        if ip:
            self.last_ip = ip
            update_fields.append("last_ip")
        if user_agent:
            self.user_agent = user_agent
            update_fields.append("user_agent")
        self.save(update_fields=update_fields)

    def __str__(self) -> str:
        """Строковое представление токена для отладки."""

        return f"Magic link for {self.user_id} (expires {self.expires_at:%Y-%m-%d %H:%M})"
