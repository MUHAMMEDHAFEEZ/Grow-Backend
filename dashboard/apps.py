from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"

    def ready(self):
        try:
            from .handlers import register_handlers
            register_handlers()
        except Exception:
            pass
