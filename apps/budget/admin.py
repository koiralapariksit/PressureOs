from django.contrib import admin

from .models import BudgetHistory


@admin.register(BudgetHistory)
class BudgetHistoryAdmin(admin.ModelAdmin):
    list_display = ("owner", "amount", "change_type", "remaining_budget", "created_at")
    list_filter = ("change_type",)
    search_fields = ("owner__username", "reason")
