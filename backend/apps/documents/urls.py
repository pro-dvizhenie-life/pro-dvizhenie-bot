from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("uploads/", views.create_upload, name="create_upload"),
    path("uploads/<uuid:version_id>/complete/", views.complete_upload, name="complete_upload"),
    path(
        "applications/<uuid:public_id>/",
        views.list_application_documents,
        name="application_documents",
    ),
    path("<uuid:document_id>/", views.delete_document, name="delete_document"),
]
