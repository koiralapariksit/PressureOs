from django.contrib import admin

from .models import AIAnalysis


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ("owner", "daily_log", "success_probability", "verdict", "generated_at")
    list_filter = ("verdict",)
    search_fields = ("owner__username", "reality_report")
