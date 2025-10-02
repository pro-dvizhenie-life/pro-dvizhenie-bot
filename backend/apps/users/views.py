"""Представления API для работы с пользователями."""

from __future__ import annotations

from config.constants import COOKIE_ACCESS_TOKEN, COOKIE_REFRESH_TOKEN
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    AuthTokensSerializer,
    LoginSerializer,
    MagicLinkLoginSerializer,
    MagicLinkRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import issue_magic_link_and_send_email, redeem_magic_link


def _issue_auth_response(request, user, *, status_code: int = status.HTTP_200_OK):
    """Выдаёт пару токенов и выставляет http-only cookies."""

    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    payload = {
        "access": str(access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }
    response = Response(payload, status=status_code)
    django_login(request, user)
    response.set_cookie(
        COOKIE_ACCESS_TOKEN,
        str(access_token),
        httponly=True,
        samesite="Lax",
        secure=False,
    )
    response.set_cookie(
        COOKIE_REFRESH_TOKEN,
        str(refresh),
        httponly=True,
        samesite="Lax",
        secure=False,
    )
    return response


class RegisterView(APIView):
    """Регистрация нового пользователя и моментальная авторизация."""

    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthTokensSerializer})
    def post(self, request):
        """Создаёт нового пользователя и сразу выдаёт токены доступа."""

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        issue_magic_link_and_send_email(user)
        return _issue_auth_response(request, user, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Логин по email/паролю с выдачей JWT и http-only cookies."""

    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses=AuthTokensSerializer)
    def post(self, request):
        """Выполняет аутентификацию по email и паролю."""

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request=request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Неверный email или пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return _issue_auth_response(request, user)


class LogoutView(APIView):
    """Выход пользователя: очищает cookies и Django-сессию."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Успешный выход")},
    )
    def post(self, request):
        """Завершает сессию пользователя и очищает cookies."""

        django_logout(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(COOKIE_ACCESS_TOKEN)
        response.delete_cookie(COOKIE_REFRESH_TOKEN)
        return response


def _get_client_ip(request) -> str | None:
    """Извлекает IP-адрес клиента из заголовков запроса."""

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class MagicLinkRequestView(APIView):
    """Отправка пользователю письма с magic link для продолжения заявки."""

    permission_classes = [AllowAny]

    @extend_schema(request=MagicLinkRequestSerializer, responses={204: None})
    def post(self, request):
        """Отправляет на почту ссылку для продолжения заявки или входа."""

        serializer = MagicLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        # Не выдаём информацию о существовании пользователя
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)
        issue_magic_link_and_send_email(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MagicLinkLoginView(APIView):
    """Авторизация по токену из письма (magic link)."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=MagicLinkLoginSerializer,
        responses={200: AuthTokensSerializer, 400: OpenApiResponse(description="Ошибка")},
    )
    def post(self, request):
        """Авторизует пользователя по валидному токену из письма."""

        serializer = MagicLinkLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user = redeem_magic_link(
            token,
            ip=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT"),
        )
        if user is None:
            return Response(
                {"detail": "Ссылка недействительна или устарела."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return _issue_auth_response(request, user)


class MeView(APIView):
    """Просмотр информации о текущем пользователе."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        """Возвращает профиль текущего авторизованного пользователя."""

        serializer = UserSerializer(request.user)
        return Response(serializer.data)
