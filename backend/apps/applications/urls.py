"""URL-маршруты приложения заявок."""

import importlib.util
from pathlib import Path

from django.urls import path

from . import views

_module_path = Path(__file__).resolve().parent / "views" / "application_views.py"
_spec = importlib.util.spec_from_file_location(
    "applications.dynamic.application_views", _module_path
)
_application_views = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_application_views)

app_name = "applications"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "forms/<slug:survey_code>/sessions/",
        _application_views.create_session,
        name="create_session",
    ),
    path("<uuid:public_id>/draft/", _application_views.get_draft, name="get_draft"),
    path(
        "<uuid:public_id>/draft/patch/",
        _application_views.patch_draft,
        name="patch_draft",
    ),
    path("<uuid:public_id>/next/", _application_views.post_next, name="post_next"),
    path("<uuid:public_id>/submit/", _application_views.post_submit, name="post_submit"),
]
