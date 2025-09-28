"""Модели и менеджеры пользователей."""

from config.constants import (
    USER_CHOICE_MAX_LENGTH,
    USER_EMAIL_MAX_LENGTH,
    USER_PHONE_MAX_LENGTH,
    USER_SESSION_TOKEN_MAX_LENGTH,
    USER_TELEGRAM_USERNAME_MAX_LENGTH,
)
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Кастомный менеджер для модели User."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
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
        return self.email

    def get_full_name(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.email
