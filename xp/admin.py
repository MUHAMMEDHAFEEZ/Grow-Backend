from django.contrib import admin
from xp.models import XPTransaction


@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "xp", "source", "created_at"]
    list_filter = ["source", "created_at"]
    search_fields = ["student__username", "student__email"]
    raw_id_fields = ["student"]
