from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone


class DeadlineEngineService:
    @staticmethod
    def build_metrics(project: Any) -> dict[str, Any]:
        today = timezone.localdate()
        start_date = project.start_date or project.created_at.date()
        deadline = project.deadline

        total_days = max((deadline - start_date).days + 1, 1)
        days_elapsed = max((today - start_date).days, 0)
        days_elapsed = min(days_elapsed, total_days)
        days_remaining = max(total_days - days_elapsed, 0)
        deadline_passed = today > deadline
        if deadline_passed:
            days_remaining = 0
            days_elapsed = total_days

        time_progress_percentage = round((days_elapsed / total_days) * 100, 2) if total_days else 0
        time_remaining_percentage = round(max(100 - time_progress_percentage, 0), 2)

        pressure_level = DeadlineEngineService.get_pressure_level(days_remaining, deadline_passed)
        project_status = pressure_level

        return {
            "start_date": start_date,
            "deadline": deadline,
            "total_days": total_days,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "deadline_passed": deadline_passed,
            "time_progress_percentage": time_progress_percentage,
            "time_remaining_percentage": time_remaining_percentage,
            "pressure_level": pressure_level,
            "project_status": project_status,
            "estimated_finish_date": DeadlineEngineService.estimate_finish_date(project, today, days_elapsed),
        }

    @staticmethod
    def get_pressure_level(days_remaining: int, deadline_passed: bool) -> str:
        if deadline_passed:
            return "Overdue"
        if days_remaining <= 0:
            return "Overdue"
        if days_remaining <= 2:
            return "Critical"
        if days_remaining <= 5:
            return "High"
        if days_remaining <= 10:
            return "Moderate"
        return "Safe"

    @staticmethod
    def estimate_finish_date(project: Any, today, days_elapsed: int):
        if project.progress_percent >= 100:
            return today
        if days_elapsed <= 0:
            return project.deadline

        pace = project.progress_percent / max(days_elapsed, 1)
        remaining_percentage = max(100 - project.progress_percent, 0)
        if pace <= 0:
            return project.deadline

        estimated_days = max(1, int(remaining_percentage / pace))
        return today + timedelta(days=estimated_days)
