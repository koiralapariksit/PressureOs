from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import Achievement, Statistics
from apps.analytics.services import award_achievement, award_xp, build_pressure_state
from apps.projects.models import Project
from apps.tracker.models import DailyLog
from django.urls import reverse


class StatisticsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stats_user", email="s@example.com", password="TestPass123")
        # create a project and a few daily logs
        proj = Project.objects.create(
            owner=self.user,
            title="Sample",
            description="Sample project",
            deadline=date.today() + timedelta(days=10),
            target_hours=20,
            expected_daily_hours=2,
            progress_percent=10,
            status=Project.Status.ACTIVE,
        )
        for i in range(3):
            DailyLog.objects.create(owner=self.user, project=proj, log_date=date.today() - timedelta(days=i), hours_worked=2.0 + i, tasks_finished=1, completed=True)

    def test_statistics_page_renders_and_contains_charts(self):
        self.client.login(username="stats_user", password="TestPass123")
        url = reverse('analytics:statistics')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'hoursWeekChart')
        self.assertContains(resp, 'hoursRangeChart')

    def test_export_csv_returns_attachment(self):
        self.client.login(username="stats_user", password="TestPass123")
        url = reverse('analytics:statistics_export_csv') + '?range=weekly'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('attachment;', resp['Content-Disposition'])
        content = resp.content.decode('utf-8')
        self.assertTrue(content.startswith('label,value'))


class PressureServiceTests(TestCase):
    def test_pressure_state_rises_for_low_completion_and_short_deadline(self):
        user = get_user_model().objects.create_user(username="pressure", email="pressure@example.com", password="StrongPass123!")
        project = Project.objects.create(
            owner=user,
            title="Stabilize the launch",
            description="Keep the release on track",
            deadline=date.today() + timedelta(days=2),
            target_hours=40,
            expected_daily_hours=8,
            progress_percent=22,
            status=Project.Status.ACTIVE,
        )
        DailyLog.objects.create(owner=user, project=project, log_date=date.today(), hours_worked=4.0, tasks_finished=1, completed=False)
        Statistics.objects.create(owner=user, hours_total=4.0, progress_score=22, failures=1, success_percentage=35, budget_remaining=1000, pressure_level=0, commits=1, focus_time_minutes=45)

        state = build_pressure_state(user)

        self.assertGreaterEqual(state["score"], 70)
        self.assertIn(state["label"], {"Red", "Black"})
        self.assertIn("pressure", state["description"].lower())


class GamificationTests(TestCase):
    def test_award_xp_and_rank_unlocks(self):
        user = get_user_model().objects.create_user(username="gamer", email="gamer@example.com", password="StrongPass123!")
        stats = Statistics.objects.create(owner=user, xp=180)
        award_xp(user, 50)
        stats.refresh_from_db()
        self.assertEqual(stats.rank_title, "Engineer")
        self.assertEqual(stats.level, 1)
        self.assertGreaterEqual(stats.xp, 230)

    def test_award_achievement_creates_badge(self):
        user = get_user_model().objects.create_user(username="badger", email="badger@example.com", password="StrongPass123!")
        achievement, created = award_achievement(user, "FIRST_SESSION", details="Completed first focus session.")
        self.assertTrue(created)
        self.assertEqual(achievement.get_achievement_type_display(), "First Session")
        self.assertEqual(Achievement.objects.filter(owner=user).count(), 1)
