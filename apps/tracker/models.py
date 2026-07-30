from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.validators import validate_non_negative, validate_positive


class DailyLog(models.Model):
    class EnergyLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        PEAK = "peak", "Peak"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_logs")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="daily_logs")
    log_date = models.DateField(default=timezone.localdate)
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, validators=[validate_non_negative])
    tasks_finished = models.PositiveIntegerField(default=0)
    github_commits = models.PositiveIntegerField(default=0)
    screenshot_proof = models.FileField(upload_to="screenshots/%Y/%m/%d/", blank=True, null=True)
    notes = models.TextField(blank=True)
    energy_level = models.CharField(max_length=20, choices=EnergyLevel.choices, default=EnergyLevel.MEDIUM)
    distractions = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-log_date"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "project", "log_date"], name="unique_daily_log_per_day")
        ]
        indexes = [
            models.Index(fields=["owner", "log_date"]),
            models.Index(fields=["project", "log_date"]),
        ]

    def clean(self) -> None:
        if self.hours_worked is not None and self.hours_worked < 0:
            raise ValidationError({"hours_worked": "Hours worked cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.owner} - {self.project.title} - {self.log_date}"


class PomodoroSession(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pomodoro_sessions")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="pomodoro_sessions", blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    focus_minutes = models.PositiveIntegerField(default=25, validators=[validate_positive])
    break_minutes = models.PositiveIntegerField(default=5, validators=[validate_positive])
    interruptions = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["owner", "started_at"]),
            models.Index(fields=["project", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner} - {self.focus_minutes}m focus"
