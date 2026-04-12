from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self) -> None:
        from core.events import EventBus, Events
        from .handlers import handle_school_member_added
        EventBus.subscribe(Events.SCHOOL_MEMBER_ADDED, handle_school_member_added)
