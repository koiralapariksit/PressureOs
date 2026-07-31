from __future__ import annotations

from decimal import Decimal
from statistics import mean

from django.db.models import Avg, Sum
from django.utils import timezone

from apps.analytics.models import Statistics
from apps.budget.models import BudgetHistory
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog, PomodoroSession


class AIJudgeService:
    def __init__(self, user):
        self.user = user

    def build_analysis(self, daily_log=None):
        project = self._get_primary_project()
        today = timezone.localdate()
        daily_log = daily_log or DailyLog.objects.filter(owner=self.user, log_date=today).order_by("-created_at").first()
        recent_logs = DailyLog.objects.filter(owner=self.user).order_by("-log_date")[:7]
        recent_hours = [float(entry.hours_worked) for entry in recent_logs] if recent_logs else [0]
        average_hours = round(mean(recent_hours), 2) if recent_hours else 0
        focus_minutes = PomodoroSession.objects.filter(owner=self.user, completed=True).aggregate(total=Sum("focus_minutes"))["total"] or 0
        consistency = self._get_consistency_score()
        budget_state = self._get_budget_state()
        failures = FailureRecord.objects.filter(project__owner=self.user).count()
        deadline = project.deadline if project else today
        remaining_days = project.days_remaining if project else 0
        days_elapsed = project.days_elapsed if project else 0
        total_days = project.total_days if project else 1
        time_progress_percentage = project.time_progress_percentage if project else 0
        current_pace = self._current_pace(project, daily_log)
        success_probability = self._calculate_probability(project, average_hours, current_pace, consistency, budget_state["current_budget"], failures, remaining_days)
        reality_report = self._build_reality_report(project, daily_log, average_hours, consistency, budget_state, failures, remaining_days, current_pace, days_elapsed, total_days, time_progress_percentage)
        recovery_plan = self._build_recovery_plan(project, average_hours, consistency, budget_state, failures, remaining_days, current_pace, time_progress_percentage)
        verdict = self._determine_verdict(success_probability)

        return {
            "project": project,
            "daily_log": daily_log,
            "reality_report": reality_report,
            "success_probability": success_probability,
            "recovery_plan": recovery_plan,
            "required_hours_tomorrow": self._required_hours_tomorrow(project, remaining_days, average_hours),
            "verdict": verdict,
            "estimated_completion": self._estimate_completion(project, average_hours, remaining_days),
            "projected_failure_date": self._projected_failure_date(project, remaining_days, average_hours),
            "budget_state": budget_state,
            "consistency": consistency,
            "failure_streak": failures,
            "current_pace": current_pace,
            "days_elapsed": days_elapsed,
            "days_remaining": remaining_days,
            "total_days": total_days,
            "time_progress_percentage": time_progress_percentage,
        }

    def _get_primary_project(self):
        return Project.objects.filter(owner=self.user).order_by("-updated_at", "deadline").first()

    def _get_consistency_score(self):
        stats = Statistics.objects.filter(owner=self.user).first()
        return int(stats.success_percentage if stats else 0)

    def _get_budget_state(self):
        latest = BudgetHistory.objects.filter(owner=self.user).order_by("-created_at").first()
        initial = BudgetHistory.get_or_create_initial_entry(self.user)
        current_budget = latest.remaining_budget if latest else initial.amount
        money_lost = max(initial.amount - current_budget, Decimal("0"))
        return {
            "initial_budget": initial.amount,
            "current_budget": current_budget,
            "money_lost": money_lost,
            "latest_penalty": latest.amount if latest and latest.change_type == BudgetHistory.ChangeType.DEDUCTION else Decimal("0"),
        }

    def _current_pace(self, project, daily_log):
        if not project:
            return 0
        if daily_log and daily_log.hours_worked:
            return float(daily_log.hours_worked)
        return float(project.expected_daily_hours or 0)

    def _calculate_probability(self, project, average_hours, current_pace, consistency, budget, failures, remaining_days):
        if not project:
            return 0
        score = 50
        if project.progress_percent >= 100:
            return 100
        if average_hours > 0:
            score += min(15, int(average_hours * 2))
        score += min(20, int(consistency / 5))
        if current_pace >= float(project.expected_daily_hours):
            score += 10
        elif current_pace > 0:
            score += 3
        if budget > Decimal("0"):
            score += 5
        if failures > 0:
            score -= min(20, failures * 4)
        if remaining_days <= 0:
            score -= 20
        return max(0, min(100, score))

    def _build_reality_report(self, project, daily_log, average_hours, consistency, budget_state, failures, remaining_days, current_pace, days_elapsed, total_days, time_progress_percentage):
        if not project:
            return "No active project exists, so there is no current execution signal to judge."
        parts = []
        if daily_log:
            parts.append(f"Today you logged {daily_log.hours_worked} hours against {project.title}.")
        else:
            parts.append(f"No work log exists for today, so the current day is still unverified.")
        parts.append(f"You have used {time_progress_percentage}% of your available time across {days_elapsed} of {total_days} days, leaving only {remaining_days} days remaining.")
        parts.append(f"Your recent average is {average_hours} hours per day, and your consistency score is {consistency}%.")
        parts.append(f"Current pace is {current_pace} hours/day against a required {project.expected_daily_hours} hours/day, so the remaining schedule is now {project.project_status.lower()}.")
        parts.append(f"Budget remaining is Rs.{budget_state['current_budget']}, with Rs.{budget_state['money_lost']} already lost and {failures} recorded failure(s).")
        return " ".join(parts)

    def _build_recovery_plan(self, project, average_hours, consistency, budget_state, failures, remaining_days, current_pace, time_progress_percentage):
        if not project:
            return "Create or assign a project before you attempt a recovery plan."
        gap = max(float(project.expected_daily_hours) - current_pace, 0)
        required_hours = max(0, round(gap + (float(project.target_hours) / max(remaining_days, 1) - current_pace), 2))
        actions = []
        actions.append(f"You have used {time_progress_percentage}% of your available time, so the next working day should target at least {required_hours:.2f} hours.")
        if consistency < 70:
            actions.append("Reduce distractions and log the work the same day instead of deferring it.")
        if budget_state["current_budget"] <= Decimal("2000"):
            actions.append("Treat the budget as a constraint and avoid further drift.")
        if failures > 0:
            actions.append("The failure streak is already visible, so the next day must be used to rebuild rhythm instead of chasing perfection.")
        return " ".join(actions)

    def _required_hours_tomorrow(self, project, remaining_days, average_hours):
        if not project:
            return 0
        remaining_hours = max(float(project.target_hours) - (average_hours * max(remaining_days, 1)), 0)
        return round(remaining_hours / max(remaining_days, 1), 2)

    def _estimate_completion(self, project, average_hours, remaining_days):
        if not project:
            return timezone.localdate()
        if average_hours <= 0:
            return timezone.localdate() + timezone.timedelta(days=30)
        target_hours = float(project.target_hours)
        average_hours_value = float(max(average_hours, 1))
        return timezone.localdate() + timezone.timedelta(days=max(1, int(target_hours / average_hours_value)))

    def _projected_failure_date(self, project, remaining_days, average_hours):
        if not project:
            return None
        if remaining_days <= 0:
            return timezone.localdate()
        return timezone.localdate() + timezone.timedelta(days=max(1, remaining_days - 1))

    def _determine_verdict(self, success_probability):
        if success_probability >= 80:
            return "stable"
        if success_probability >= 55:
            return "warning"
        return "critical"
