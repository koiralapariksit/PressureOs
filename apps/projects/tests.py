from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import FailureRecord, Project


class ProjectWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="builder",
            email="builder@example.com",
            password="strong-pass-123",
        )
        self.client.force_login(self.user)

    def test_deadline_engine_properties_are_reusable_and_time_based(self):
        today = timezone.localdate()
        project = Project.objects.create(
            owner=self.user,
            title="Launch beta",
            start_date=today - timedelta(days=1),
            deadline=today + timedelta(days=7),
            target_hours=40,
            expected_daily_hours=4,
            progress_percent=25,
        )

        self.assertEqual(project.total_days, 8)
        self.assertEqual(project.days_elapsed, 1)
        self.assertEqual(project.days_remaining, 7)
        self.assertEqual(project.time_progress_percentage, 12.5)
        self.assertEqual(project.time_remaining_percentage, 87.5)
        self.assertFalse(project.deadline_passed)
        self.assertEqual(project.project_status, "Moderate")

    def test_past_deadline_is_rejected_on_backend(self):
        response = self.client.post(
            reverse("projects:create"),
            {
                "title": "Historic mission",
                "description": "This should fail.",
                "start_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "deadline": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "target_hours": 24,
                "expected_daily_hours": 4,
                "priority": "high",
                "github_repository": "https://github.com/example/onboarding",
                "progress_percent": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(title="Historic mission").exists())

    def test_project_metrics_are_calculated(self):
        project = Project.objects.create(
            owner=self.user,
            title="Launch beta",
            deadline=date.today() + timedelta(days=10),
            target_hours=40,
            expected_daily_hours=4,
            progress_percent=25,
        )

        self.assertEqual(project.remaining_days, 10)
        self.assertEqual(project.required_hours_per_day, 4)
        self.assertEqual(project.completion_percentage, 25)
        self.assertGreaterEqual(project.days_behind, 0)

    def test_user_can_create_and_archive_project(self):
        response = self.client.post(
            reverse("projects:create"),
            {
                "title": "Refine onboarding",
                "description": "Ship the onboarding flow.",
                "deadline": (date.today() + timedelta(days=7)).isoformat(),
                "target_hours": 24,
                "expected_daily_hours": 4,
                "priority": "high",
                "github_repository": "https://github.com/example/onboarding",
                "progress_percent": 10,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(title="Refine onboarding")
        self.assertEqual(project.owner, self.user)

        archive_response = self.client.post(reverse("projects:archive", args=[project.pk]))
        self.assertEqual(archive_response.status_code, 302)
        project.refresh_from_db()
        self.assertFalse(project.is_active)
        self.assertEqual(project.status, Project.Status.PAUSED)

    def test_user_can_complete_project(self):
        project = Project.objects.create(
            owner=self.user,
            title="Publish release",
            deadline=date.today() + timedelta(days=3),
            target_hours=12,
            expected_daily_hours=4,
            progress_percent=80,
        )

        response = self.client.post(reverse("projects:complete", args=[project.pk]))
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.COMPLETED)
        self.assertEqual(project.progress_percent, 100)

    def test_hall_of_shame_view_shows_failed_project(self):
        project = Project.objects.create(
            owner=self.user,
            title="Failed MVP",
            deadline=date.today() + timedelta(days=7),
            target_hours=20,
            expected_daily_hours=4,
            progress_percent=20,
            status=Project.Status.FAILED,
            is_active=False,
        )
        FailureRecord.objects.create(
            project=project,
            failure_date=date.today() - timedelta(days=2),
            reason="Missed the deadline",
            days_lost=3,
        )

        response = self.client.get(reverse("projects:hall_of_shame"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hall of Shame")
        self.assertContains(response, project.title)
        self.assertContains(response, "Missed the deadline")
        self.assertContains(response, "$")
        self.assertContains(response, "Days lost")
