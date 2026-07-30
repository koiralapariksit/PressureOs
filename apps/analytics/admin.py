from django.contrib import admin

from .models import Achievement, Statistics


@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = ("owner", "hours_total", "failures", "success_percentage", "pressure_level", "updated_at")
    search_fields = ("owner__username",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("owner", "achievement_type", "earned_at")
    list_filter = ("achievement_type",)
    search_fields = ("owner__username", "details")
