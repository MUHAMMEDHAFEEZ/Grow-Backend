from django.contrib import admin

from .models import RegistrationCode


@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "school", "grade", "code_type", "is_used", "created_at")
    list_filter = ("school", "code_type", "is_used")
    search_fields = ("code",)
