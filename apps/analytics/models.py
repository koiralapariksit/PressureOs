from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.validators import validate_non_negative, validate_percentage


class Statistics(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="statistics")
    hours_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[validate_non_negative])
    progress_score = models.PositiveIntegerField(default=0, validators=[validate_percentage])
    failures = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    success_percentage = models.PositiveIntegerField(default=0, validators=[validate_percentage])
    budget_remaining = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[validate_non_negative])
    pressure_level = models.PositiveIntegerField(default=0, validators=[validate_percentage])
    commits = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    focus_time_minutes = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    xp = models.PositiveIntegerField(default=0, validators=[validate_non_negative])
    updated_at = models.DateTimeField(default=timezone.now)

    RANK_THRESHOLDS = [
        (0, "Builder"),
        (200, "Engineer"),
        (500, "Creator"),
        (1000, "Architect"),
        (2000, "Master"),
        (3500, "Legend"),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Statistics for {self.owner}"

    @property
    def rank_title(self) -> str:
        current_rank = "Builder"
        for threshold, label in self.RANK_THRESHOLDS:
            if self.xp >= threshold:
                current_rank = label
        return current_rank

    @property
    def level(self) -> int:
        return int(self.xp // 250) + 1

    @property
    def current_rank_threshold(self) -> int:
        threshold = 0
        for value, _ in self.RANK_THRESHOLDS:
            if self.xp >= value:
                threshold = value
        return threshold

    @property
    def next_rank_threshold(self) -> int | None:
        for value, _ in self.RANK_THRESHOLDS:
            if value > self.xp:
                return value
        return None

    @property
    def xp_to_next_rank(self) -> int:
        target = self.next_rank_threshold
        return max(0, target - self.xp) if target is not None else 0

    @property
    def rank_progress(self) -> int:
        next_threshold = self.next_rank_threshold
        if next_threshold is None:
            return 100
        current = self.current_rank_threshold
        progress = int(((self.xp - current) / max(next_threshold - current, 1)) * 100)
        return max(0, min(100, progress))


class Achievement(models.Model):
    class AchievementType(models.TextChoices):
        STREAK_30 = "30_day_streak", "30 Day Streak"
        HOURS_100 = "100_hours", "100 Hours"
        NO_FAILURE_MONTH = "no_failure_month", "No Failure Month"
        IMPOSSIBLE_PROJECT = "impossible_project", "Complete Impossible Project"
        HOURS_500 = "500_hours", "500 Hours"
        FIRST_SESSION = "first_session", "First Session"
        FOCUS_FLOW = "focus_flow", "Focus Flow"
        FULL_THROTTLE = "full_throttle", "Full Throttle"
        PROJECT_ARCHITECT = "project_architect", "Project Architect"
        LEGEND = "legend", "Legend"
        HALL_OF_VICTORY = "hall_of_victory", "Hall of Victory"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement_type = models.CharField(max_length=40, choices=AchievementType.choices)
    earned_at = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-earned_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "achievement_type"], name="unique_achievement_per_user")
        ]
        indexes = [
            models.Index(fields=["owner", "earned_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner} - {self.get_achievement_type_display()}"
