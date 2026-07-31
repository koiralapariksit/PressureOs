from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Project
from apps.tracker.models import DailyLog


class DailyCheckInTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="trackeruser", password="secret123")
        self.project = Project.objects.create(
            owner=self.user,
            title="Launch sprint",
            deadline=date.today(),
            target_hours=40,
            expected_daily_hours=8,
            progress_percent=10,
        )

    def test_check_in_creates_daily_log_and_redirects(self):
        self.assertTrue(self.client.login(username="trackeruser", password="secret123"))
        response = self.client.post(
            reverse("tracker:checkin"),
            {
                "project": self.project.pk,
                "hours_worked": 7.5,
                "tasks_finished": 3,
                "notes": "Shipped a meaningful chunk.",
                "energy_level": DailyLog.EnergyLevel.HIGH,
                "github_commits": 2,
                "distractions": 1,
                "completed": True,
            },
        )
        self.assertRedirects(response, reverse("tracker:checkin_success"))
        self.assertTrue(DailyLog.objects.filter(owner=self.user, log_date=timezone.localdate()).exists())

    def test_duplicate_check_in_updates_existing_daily_log(self):
        self.assertTrue(self.client.login(username="trackeruser", password="secret123"))

        first_response = self.client.post(
            reverse("tracker:checkin"),
            {
                "project": self.project.pk,
                "hours_worked": 7.5,
                "tasks_finished": 3,
                "notes": "Initial submission.",
                "energy_level": DailyLog.EnergyLevel.MEDIUM,
                "github_commits": 1,
                "distractions": 0,
                "completed": False,
            },
        )
        self.assertRedirects(first_response, reverse("tracker:checkin_success"))

        second_response = self.client.post(
            reverse("tracker:checkin"),
            {
                "project": self.project.pk,
                "hours_worked": 4.0,
                "tasks_finished": 1,
                "notes": "Updated submission.",
                "energy_level": DailyLog.EnergyLevel.HIGH,
                "github_commits": 2,
                "distractions": 1,
                "completed": True,
            },
        )
        self.assertRedirects(second_response, reverse("tracker:checkin_success"))

        daily_logs = DailyLog.objects.filter(owner=self.user, project=self.project, log_date=timezone.localdate())
        self.assertEqual(daily_logs.count(), 1)
        daily_log = daily_logs.get()
        self.assertEqual(daily_log.hours_worked, Decimal("4.0"))
        self.assertEqual(daily_log.tasks_finished, 1)
        self.assertEqual(daily_log.notes, "Updated submission.")
        self.assertTrue(daily_log.completed)
