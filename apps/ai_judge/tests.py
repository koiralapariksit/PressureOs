from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.ai_judge.services import AIJudgeService
from apps.budget.models import BudgetHistory
from apps.projects.models import Project
from apps.tracker.models import DailyLog


class AIJudgeServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="judgeuser", email="judge@example.com", password="strong-pass")
        self.project = Project.objects.create(
            owner=self.user,
            title="Launch the product",
            deadline=date.today() + timedelta(days=7),
            target_hours=40,
            expected_daily_hours=6,
            progress_percent=20,
        )
        DailyLog.objects.create(
            owner=self.user,
            project=self.project,
            log_date=date.today(),
            hours_worked=3,
            tasks_finished=2,
            notes="Worked on the MVP",
        )
        BudgetHistory.get_or_create_initial_entry(self.user)

    def test_analysis_returns_factual_report_and_plan(self):
        payload = AIJudgeService(self.user).build_analysis()
        self.assertIn("hours", payload["reality_report"])
        self.assertIn("hours", payload["recovery_plan"])
        self.assertIn("required_hours_tomorrow", payload)
        self.assertIn(payload["verdict"], {"warning", "critical", "stable"})


class AIJudgeViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="judgeview", email="judgeview@example.com", password="strong-pass")
        self.client.force_login(self.user)

    def test_ai_judge_page_renders_with_daily_log(self):
        project = Project.objects.create(
            owner=self.user,
            title="Test product",
            deadline=date.today() + timedelta(days=7),
            target_hours=30,
            expected_daily_hours=5,
            progress_percent=40,
        )
        DailyLog.objects.create(
            owner=self.user,
            project=project,
            log_date=date.today(),
            hours_worked=3,
            tasks_finished=1,
            notes="Started the sprint",
        )

        response = self.client.get(reverse("ai_judge:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Judge")
        self.assertContains(response, "Success probability")
        self.assertContains(response, "Required hours tomorrow")

    def test_ai_judge_page_renders_without_daily_logs(self):
        response = self.client.get(reverse("ai_judge:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Judge")
        self.assertContains(response, "No AI judgments yet")
