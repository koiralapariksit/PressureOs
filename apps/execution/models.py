from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.core.validators import validate_non_negative, validate_positive


class FocusSession(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ABORTED = "aborted", "Aborted"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="focus_sessions", blank=True, null=True)
    operation_name = models.CharField(max_length=200, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    active_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    paused_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    total_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    last_activity_at = models.DateTimeField(default=timezone.now)
    idle_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["owner", "started_at"]),
            models.Index(fields=["project", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner} - {self.project.title if self.project else 'No project'} - {self.started_at.date()}"


@receiver(post_save, sender=FocusSession)
def refresh_focus_summary_on_session_save(sender, instance, **kwargs):
    from apps.execution.services import ExecutionService

    if instance.owner_id:
        ExecutionService.refresh_daily_summary(instance.owner_id, instance.started_at.date())


@receiver(post_delete, sender=FocusSession)
def refresh_focus_summary_on_session_delete(sender, instance, **kwargs):
    from apps.execution.services import ExecutionService

    if instance.owner_id:
        ExecutionService.refresh_daily_summary(instance.owner_id, instance.started_at.date())


class SessionPause(models.Model):
    focus_session = models.ForeignKey(FocusSession, on_delete=models.CASCADE, related_name="pauses")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["started_at"]

    def __str__(self) -> str:
        return f"Pause for {self.focus_session_id}"


class DailyWorkSummary(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_work_summaries")
    log_date = models.DateField(default=timezone.localdate)
    total_active_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    total_paused_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    total_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    focus_sessions_count = models.PositiveIntegerField(default=0, validators=[validate_positive])
    average_session_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    longest_session_seconds = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "log_date"], name="unique_daily_work_summary_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.owner} - {self.log_date}"
