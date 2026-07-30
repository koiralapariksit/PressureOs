from django.contrib import admin

from .models import FailureRecord, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "deadline", "progress_percent", "is_active")
    list_filter = ("status", "difficulty", "priority", "is_active")
    search_fields = ("title", "description", "github_repository")
    ordering = ("deadline",)


@admin.register(FailureRecord)
class FailureRecordAdmin(admin.ModelAdmin):
    list_display = ("project", "failure_date", "days_lost")
    search_fields = ("project__title", "reason")
