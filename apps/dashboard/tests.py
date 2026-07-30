from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.budget.models import BudgetHistory
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog, PomodoroSession
from apps.analytics.models import Statistics


class DashboardViewTests(TestCase):
    def test_dashboard_renders_core_metrics(self):
        user = get_user_model().objects.create_user(username="ops", email="ops@example.com", password="StrongPass123!")
        project = Project.objects.create(
            owner=user,
            title="Ship the pressure engine",
            description="Finish the operational core",
            deadline=date.today() + timedelta(days=6),
            target_hours=40,
            expected_daily_hours=8,
            progress_percent=62,
            status=Project.Status.ACTIVE,
        )
        DailyLog.objects.create(owner=user, project=project, log_date=date.today(), hours_worked=6.5, tasks_finished=3, completed=True)
        DailyLog.objects.create(owner=user, project=project, log_date=date.today() - timedelta(days=1), hours_worked=5, tasks_finished=2, completed=True)
        PomodoroSession.objects.create(owner=user, project=project, focus_minutes=90, completed=True)
        BudgetHistory.objects.create(owner=user, amount=2000, change_type=BudgetHistory.ChangeType.INITIAL, remaining_budget=1200)
        FailureRecord.objects.create(project=project, failure_date=date.today() - timedelta(days=2), reason="Missed a sprint", days_lost=1)
        Statistics.objects.create(owner=user, hours_total=11.5, progress_score=62, failures=1, success_percentage=80, budget_remaining=1200, pressure_level=72, commits=5, focus_time_minutes=90)

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's Mission")
        self.assertContains(response, "Pressure Meter")
        self.assertContains(response, "Current project")
        self.assertContains(response, "Recent Activity")
        self.assertEqual(response.context["completion_percent"], 62)
        self.assertEqual(response.context["focus_hours"], 1.5)
