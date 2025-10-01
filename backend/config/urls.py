from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from users.views import (
    LoginView,
    LogoutView,
    MagicLinkLoginView,
    MagicLinkRequestView,
    RegisterView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login/", LoginView.as_view(), name="login"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path(
        "api/v1/auth/magic-link/request/",
        MagicLinkRequestView.as_view(),
        name="magic-link-request",
    ),
    path(
        "api/v1/auth/magic-link/login/",
        MagicLinkLoginView.as_view(),
        name="magic-link-login",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/users/", include("users.urls")),
    path("api/v1/applications/", include("applications.urls")),
    path("api/v1/documents/", include("documents.urls")),
]
