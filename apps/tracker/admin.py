from django.contrib import admin

from .models import DailyLog, PomodoroSession


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ("owner", "project", "log_date", "hours_worked", "completed")
    list_filter = ("completed", "energy_level")
    search_fields = ("owner__username", "project__title", "notes")


@admin.register(PomodoroSession)
class PomodoroSessionAdmin(admin.ModelAdmin):
    list_display = ("owner", "project", "started_at", "focus_minutes", "interruptions", "completed")
    list_filter = ("completed",)
    search_fields = ("owner__username", "project__title")
