"""Представления API для работы с пользователями."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    AuthTokensSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _issue_auth_response(request, user, *, status_code: int = 200):
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
        "access_token",
        str(access_token),
        httponly=True,
        samesite="Lax",
        secure=False,
    )
    response.set_cookie(
        "refresh_token",
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
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _issue_auth_response(request, user, status_code=201)


class LoginView(APIView):
    """Логин по email/паролю с выдачей JWT и http-only cookies."""

    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses=AuthTokensSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request=request, username=email, password=password)
        if user is None:
            return Response({"detail": "Неверный email или пароль."}, status=400)
        return _issue_auth_response(request, user)


class LogoutView(APIView):
    """Выход пользователя: очищает cookies и Django-сессию."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Успешный выход")},
    )
    def post(self, request):
        django_logout(request)
        response = Response(status=204)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class MeView(APIView):
    """Просмотр информации о текущем пользователе."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
