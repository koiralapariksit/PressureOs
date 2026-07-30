from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.validators import validate_percentage


class AIAnalysis(models.Model):
    class Verdict(models.TextChoices):
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"
        STABLE = "stable", "Stable"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_analyses")
    daily_log = models.OneToOneField("tracker.DailyLog", on_delete=models.CASCADE, related_name="ai_analysis")
    reality_report = models.TextField()
    success_probability = models.PositiveIntegerField(default=0, validators=[validate_percentage])
    estimated_completion = models.DateField(blank=True, null=True)
    projected_failure_date = models.DateField(blank=True, null=True)
    average_hours_needed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    recovery_plan = models.TextField(blank=True)
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.WARNING)
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["owner", "generated_at"]),
            models.Index(fields=["daily_log", "generated_at"]),
        ]

    def __str__(self) -> str:
        return f"AI analysis for {self.daily_log}"