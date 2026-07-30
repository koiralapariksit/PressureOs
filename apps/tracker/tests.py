from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
        self.assertTrue(DailyLog.objects.filter(owner=self.user, log_date=date.today()).exists())
