from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.analytics.models import Achievement, Statistics
from apps.analytics.services import build_pressure_state
from apps.budget.models import BudgetHistory
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog, PomodoroSession


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        project = (
            Project.objects.filter(owner=user).order_by("-updated_at", "deadline").first()
            or Project(owner=user, title="No current project", deadline=timezone.localdate() + timedelta(days=7), target_hours=40, expected_daily_hours=8)
        )

        today = timezone.localdate()
        today_logs = DailyLog.objects.filter(owner=user, log_date=today)
        today_hours = sum(float(entry.hours_worked) for entry in today_logs) if today_logs.exists() else 0
        focus_minutes = PomodoroSession.objects.filter(owner=user, completed=True).aggregate(total=Sum("focus_minutes"))["total"] or 0
        focus_hours = round(focus_minutes / 60, 1)

        latest_budget = BudgetHistory.objects.filter(owner=user).order_by("-created_at").first()
        stats = Statistics.objects.filter(owner=user).first()
        recent_badges = Achievement.objects.filter(owner=user).order_by("-earned_at")[:4]
        failures = FailureRecord.objects.filter(project__owner=user).count()

        completion_percent = int(project.progress_percent if project.pk else 0)
        pressure_meter = int(stats.pressure_level if stats else 0)
        consistency_score = int(stats.success_percentage if stats else 0)
        money_remaining = float(latest_budget.remaining_budget if latest_budget else 0)

        recent_activity = []
        for log in DailyLog.objects.filter(owner=user).order_by("-log_date")[:4]:
            recent_activity.append({
                "title": f"{log.project.title} - {log.hours_worked}h logged",
                "detail": log.notes or "Momentum maintained.",
                "time": log.log_date.strftime("%b %d"),
            })

        if not recent_activity:
            recent_activity = [
                {"title": "No activity yet", "detail": "Begin your first mission to populate the board.", "time": "Now"},
            ]

        latest_log = DailyLog.objects.filter(owner=user).order_by("-log_date", "-created_at").first()
        checkin_summary = None
        if latest_log:
            checkin_summary = {
                "project": latest_log.project.title,
                "hours": latest_log.hours_worked,
                "tasks": latest_log.tasks_finished,
                "energy": latest_log.get_energy_level_display(),
                "completed": latest_log.completed,
                "notes": latest_log.notes or "No extra notes captured.",
            }

        recent_checkins = []
        for log in DailyLog.objects.filter(owner=user).order_by("-log_date", "-created_at")[:5]:
            recent_checkins.append({
                "date": log.log_date.strftime("%b %d"),
                "project": log.project.title,
                "hours": log.hours_worked,
                "completed": log.completed,
            })

        pressure_state = build_pressure_state(user)

        context.update({
            "page_title": "Execution Dashboard",
            "project": project,
            "today_mission": project.title if project.pk else "Define the first mission",
            "countdown": (project.deadline - today).days,
            "completion_percent": completion_percent,
            "pressure_meter": pressure_state["score"],
            "pressure_label": pressure_state["label"],
            "pressure_description": pressure_state["description"],
            "pressure_theme": pressure_state["theme"],
            "pressure_shell_class": pressure_state["shell_class"],
            "pressure_panel_class": pressure_state["panel_class"],
            "pressure_pill_class": pressure_state["pill_class"],
            "pressure_accent_class": pressure_state["accent_class"],
            "pressure_muted_class": pressure_state["muted_class"],
            "money_remaining": money_remaining,
            "failure_streak": failures,
            "consistency_score": consistency_score,
            "focus_hours": focus_hours,
            "today_hours": round(today_hours, 1),
            "rank_title": stats.rank_title if stats else "Builder",
            "level": stats.level if stats else 1,
            "current_xp": int(stats.xp if stats else 0),
            "rank_progress": stats.rank_progress if stats else 0,
            "next_rank_threshold": stats.next_rank_threshold if stats else 200,
            "recent_badges": recent_badges,
            "recent_activity": recent_activity,
            "checkin_summary": checkin_summary,
            "recent_checkins": recent_checkins,
            "chart_points": [62, 78, 74, 88, 92],
        })
        return context
