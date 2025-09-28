from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self) -> None:  # pragma: no cover - import side effect only
        from . import signals  # noqa: F401 -- ensure signal registration
