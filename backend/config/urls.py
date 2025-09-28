from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
                                   SpectacularAPIView,
                                   SpectacularRedocView,
                                   SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="api-redoc",
    ),
    path("api/v1/users/", include("users.urls")),
    path("api/v1/applications/", include("applications.urls")),
    path("api/v1/documents/", include("documents.urls")),
]
