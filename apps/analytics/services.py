from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.analytics.models import Statistics
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog
from apps.pomodoro.models import PomodoroSession
from datetime import timedelta


def build_pressure_state(user: Any) -> dict[str, Any]:
    project = Project.objects.filter(owner=user).order_by("-updated_at", "deadline").first()
    stats = Statistics.objects.filter(owner=user).first()
    failures = FailureRecord.objects.filter(project__owner=user).count()

    progress_percent = int(project.progress_percent if project and project.pk else 0)
    consistency_score = int(stats.success_percentage if stats else 0)
    hours_total = float(stats.hours_total if stats else 0)

    deadline_days = (project.deadline - timezone.localdate()).days if project and project.deadline else 30

    deadline_pressure = 0
    if deadline_days <= 0:
        deadline_pressure = 32
    elif deadline_days <= 2:
        deadline_pressure = 26
    elif deadline_days <= 5:
        deadline_pressure = 18
    elif deadline_days <= 10:
        deadline_pressure = 10

    progress_pressure = max(0, (100 - progress_percent) * 0.7)
    consistency_pressure = max(0, (100 - consistency_score) * 0.5)
    failure_pressure = min(24, failures * 8)

    if project and project.target_hours:
        target_hours = float(project.target_hours)
        pace_pressure = max(0, min(20, int(((target_hours - hours_total) / max(target_hours, 1)) * 18)))
    else:
        pace_pressure = 0

    score = min(100, int(deadline_pressure + progress_pressure + consistency_pressure + failure_pressure + pace_pressure))

    # Integrate Pomodoro focus score (last 7 days) to reduce pressure when focus is high
    try:
        window = timezone.now() - timedelta(days=7)
        sessions = PomodoroSession.objects.filter(owner=user, created_at__gte=window)
        completed = sessions.filter(completed=True).count()
        interruptions = sum(s.interruptions or 0 for s in sessions)
        focus_percent = 0
        if completed + interruptions > 0:
            focus_percent = int(max(0, min(100, (completed / (completed + interruptions)) * 100)))
        # Higher focus_percent reduces pressure by up to 8 points
        focus_reduction = int((focus_percent / 100.0) * 8)
        score = max(0, score - focus_reduction)
    except Exception:
        # on any error, skip focus integration
        pass

    if score >= 85:
        label = "Black"
        description = "Pressure is critical. The system is under maximum strain."
        theme = "black"
    elif score >= 70:
        label = "Red"
        description = "Pressure is severe. Immediate focus is required to recover control."
        theme = "red"
    elif score >= 50:
        label = "Orange"
        description = "Pressure is building. Tighten execution and close the gap."
        theme = "orange"
    elif score >= 30:
        label = "Yellow"
        description = "Pressure is rising. Steady effort will restore balance."
        theme = "yellow"
    else:
        label = "Green"
        description = "Pressure is stable. The mission remains under control."
        theme = "green"

    theme_map = {
        "green": {
            "body_class": "",
            "shell_class": "border-emerald-400/20",
            "panel_class": "border-emerald-400/20 bg-emerald-500/10",
            "pill_class": "border-emerald-400/20 bg-emerald-500/10 text-emerald-200",
            "accent_class": "text-emerald-300",
            "muted_class": "text-emerald-200/80",
        },
        "yellow": {
            "body_class": "",
            "shell_class": "border-amber-400/20",
            "panel_class": "border-amber-400/20 bg-amber-500/10",
            "pill_class": "border-amber-400/20 bg-amber-500/10 text-amber-200",
            "accent_class": "text-amber-300",
            "muted_class": "text-amber-200/80",
        },
        "orange": {
            "body_class": "",
            "shell_class": "border-orange-400/20",
            "panel_class": "border-orange-400/20 bg-orange-500/10",
            "pill_class": "border-orange-400/20 bg-orange-500/10 text-orange-200",
            "accent_class": "text-orange-300",
            "muted_class": "text-orange-200/80",
        },
        "red": {
            "body_class": "",
            "shell_class": "border-red-500/20",
            "panel_class": "border-red-500/20 bg-red-500/10",
            "pill_class": "border-red-500/20 bg-red-500/10 text-red-200",
            "accent_class": "text-red-300",
            "muted_class": "text-red-200/80",
        },
        "black": {
            "body_class": "",
            "shell_class": "border-zinc-400/20",
            "panel_class": "border-zinc-400/20 bg-zinc-500/10",
            "pill_class": "border-zinc-400/20 bg-zinc-500/10 text-zinc-200",
            "accent_class": "text-zinc-300",
            "muted_class": "text-zinc-200/80",
        },
    }

    style = theme_map[theme]
    return {
        "score": score,
        "label": label,
        "description": description,
        "theme": theme,
        "body_class": style["body_class"],
        "shell_class": style["shell_class"],
        "panel_class": style["panel_class"],
        "pill_class": style["pill_class"],
        "accent_class": style["accent_class"],
        "muted_class": style["muted_class"],
    }


from django.contrib import messages

from .models import Achievement, Statistics


def get_statistics(owner):
    stats, _ = Statistics.objects.get_or_create(owner=owner)
    return stats


def award_xp(owner, xp, request=None):
    if xp <= 0:
        return get_statistics(owner)

    stats = get_statistics(owner)
    previous_rank = stats.rank_title
    stats.xp = stats.xp + xp
    stats.save(update_fields=["xp", "updated_at"])

    if request and stats.rank_title != previous_rank:
        messages.success(request, f"Rank unlocked: {stats.rank_title}! Keep pushing your progress.")

    return stats


def award_achievement(owner, achievement_type, details="", request=None):
    resolved_type = achievement_type
    try:
        resolved_type = Achievement.AchievementType[achievement_type].value
    except (KeyError, TypeError):
        # If the provided achievement_type is already a valid value or invalid, keep as-is.
        pass

    achievement, created = Achievement.objects.get_or_create(
        owner=owner,
        achievement_type=resolved_type,
        defaults={"details": details},
    )
    if created and request:
        messages.success(request, f"Badge unlocked: {achievement.get_achievement_type_display()}.")
    return achievement, created
