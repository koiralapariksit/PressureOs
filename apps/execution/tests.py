from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.execution.models import DailyWorkSummary, FocusSession, SessionPause
from apps.execution.services import ExecutionService
from apps.projects.models import Project


class ExecutionTrackingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="executionuser", password="secret123")
        self.project = Project.objects.create(
            owner=self.user,
            title="Launch sprint",
            deadline=date.today(),
            target_hours=40,
            expected_daily_hours=8,
            progress_percent=10,
        )

    def test_starting_session_creates_active_focus_session(self):
        self.client.login(username="executionuser", password="secret123")
        response = self.client.post(
            reverse("execution:start"),
            {"project": self.project.pk, "operation_name": "Architecture review"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FocusSession.objects.filter(owner=self.user, status=FocusSession.Status.RUNNING).exists())

    def test_finish_session_updates_daily_summary(self):
        session = FocusSession.objects.create(owner=self.user, project=self.project, operation_name="Shipping", status=FocusSession.Status.RUNNING)
        session.status = FocusSession.Status.COMPLETED
        session.total_seconds = 3600
        session.save(update_fields=["status", "total_seconds", "updated_at"])
        summary = DailyWorkSummary.objects.filter(owner=self.user, log_date=date.today()).first()
        self.assertIsNotNone(summary)
        self.assertEqual(summary.focus_sessions_count, 1)
        self.assertEqual(summary.total_seconds, 3600)

    def test_idle_timeout_auto_pauses_session(self):
        session = FocusSession.objects.create(
            owner=self.user,
            project=self.project,
            operation_name="Deep work",
            status=FocusSession.Status.RUNNING,
            started_at=timezone.now() - timezone.timedelta(minutes=10),
            last_activity_at=timezone.now() - timezone.timedelta(minutes=6),
        )

        updated_session = ExecutionService.pause_if_idle(session, now=timezone.now())

        self.assertEqual(updated_session.status, FocusSession.Status.PAUSED)
        self.assertTrue(SessionPause.objects.filter(focus_session=session, reason="idle_timeout").exists())
