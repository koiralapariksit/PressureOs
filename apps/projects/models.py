from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import date, timedelta

from apps.core.validators import validate_non_negative, validate_percentage, validate_positive
from apps.projects.services import DeadlineEngineService


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
    start_date = models.DateField(default=timezone.localdate)
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
        today = timezone.localdate()
        if not self.start_date:
            raise ValidationError({"start_date": "Project start date is required."})
        if not self.deadline:
            raise ValidationError({"deadline": "Deadline is required."})
        if self.deadline < today:
            raise ValidationError({"deadline": "Deadline cannot be in the past."})
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError({"deadline": "Deadline must be on or after the project start date."})
        if self.target_hours <= 0:
            raise ValidationError({"target_hours": "Target hours must be greater than zero."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    @property
    def total_days(self) -> int:
        return max((self.deadline - self.start_date).days, 1)

    @property
    def days_elapsed(self) -> int:
        today = timezone.localdate()
        if today < self.start_date:
            return 0
        elapsed = (today - self.start_date).days
        return min(max(elapsed, 0), self.total_days)

    @property
    def days_remaining(self) -> int:
        if self.deadline_passed:
            return 0
        return max(self.total_days - self.days_elapsed, 0)

    @property
    def deadline_passed(self) -> bool:
        return timezone.localdate() > self.deadline

    @property
    def time_progress_percentage(self) -> float:
        if not self.total_days:
            return 0.0
        return round((self.days_elapsed / self.total_days) * 100, 2)

    @property
    def time_remaining_percentage(self) -> float:
        return round(max(100 - self.time_progress_percentage, 0), 2)

    @property
    def pressure_level(self) -> str:
        return DeadlineEngineService.get_pressure_level(self.days_remaining, self.deadline_passed)

    @property
    def project_status(self) -> str:
        return self.pressure_level

    @property
    def estimated_finish_date(self):
        today = timezone.localdate()
        if self.progress_percent >= 100:
            return today
        if self.days_elapsed <= 0:
            return self.deadline
        pace = self.progress_percent / max(self.days_elapsed, 1)
        remaining_percentage = max(100 - self.progress_percent, 0)
        if pace <= 0:
            return self.deadline
        estimated_days = max(1, int(remaining_percentage / pace))
        return today + timedelta(days=estimated_days)

    @property
    def remaining_days(self) -> int:
        return self.days_remaining

    @property
    def required_hours_per_day(self) -> float:
        return round(float(self.target_hours) / max(self.days_remaining, 1), 2) if self.target_hours else 0

    @property
    def completion_percentage(self) -> int:
        return int(self.progress_percent)

    @property
    def days_behind(self) -> int:
        if self.progress_percent >= 100:
            return 0
        if self.days_remaining <= 0:
            return max(0, int(self.progress_percent // 10) - 1)
        expected_progress = max(0, int((100 - self.progress_percent) / max(self.days_remaining, 1)))
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
