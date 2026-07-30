from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import date

from apps.core.validators import validate_non_negative, validate_percentage, validate_positive


class Project(models.Model):
    class Category(models.TextChoices):
        PRODUCT = "product", "Product"
        BUSINESS = "business", "Business"
        CREATIVE = "creative", "Creative"
        TECHNICAL = "technical", "Technical"
        RESEARCH = "research", "Research"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MODERATE = "moderate", "Moderate"
        HARD = "hard", "Hard"
        INSANE = "insane", "Insane"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PAUSED = "paused", "Paused"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.PRODUCT)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MODERATE)
    deadline = models.DateField()
    target_hours = models.DecimalField(max_digits=8, decimal_places=2, validators=[validate_positive])
    expected_daily_hours = models.DecimalField(max_digits=6, decimal_places=2, validators=[validate_positive])
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.HIGH)
    github_repository = models.URLField(blank=True)
    progress_percent = models.PositiveIntegerField(default=0, validators=[validate_percentage])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "deadline"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["deadline"]),
            models.Index(fields=["is_active", "status"]),
        ]

    def clean(self) -> None:
        if self.deadline and self.created_at and self.deadline < self.created_at.date():
            raise ValidationError({"deadline": "Deadline cannot be in the past."})
        if self.target_hours <= 0:
            raise ValidationError({"target_hours": "Target hours must be greater than zero."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    @property
    def remaining_days(self) -> int:
        today = date.today()
        return max((self.deadline - today).days, 0)

    @property
    def required_hours_per_day(self) -> float:
        return round(float(self.target_hours) / max(self.remaining_days, 1), 2) if self.target_hours else 0

    @property
    def completion_percentage(self) -> int:
        return int(self.progress_percent)

    @property
    def days_behind(self) -> int:
        if self.progress_percent >= 100:
            return 0
        if self.remaining_days <= 0:
            return max(0, int(self.progress_percent // 10) - 1)
        expected_progress = max(0, int((100 - self.progress_percent) / max(self.remaining_days, 1)))
        return max(0, expected_progress)


class FailureRecord(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="failure_records")
    failure_date = models.DateField(default=date.today)
    reason = models.TextField(blank=True)
    days_lost = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-failure_date"]
        indexes = [
            models.Index(fields=["project", "failure_date"]),
        ]

    def __str__(self) -> str:
        return f"Failure for {self.project.title} on {self.failure_date}"
