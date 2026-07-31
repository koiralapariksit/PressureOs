from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.execution.models import DailyWorkSummary, FocusSession, SessionPause


class ExecutionService:
    @staticmethod
    def get_or_create_active_session(owner, project=None, operation_name="") -> FocusSession:
        session = FocusSession.objects.filter(owner=owner, status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]).order_by("-started_at").first()
        if session:
            if project is not None and session.project_id != project.pk:
                session.project = project
                session.save(update_fields=["project", "updated_at"])
            if operation_name and not session.operation_name:
                session.operation_name = operation_name
                session.save(update_fields=["operation_name", "updated_at"])
            return session

        return FocusSession.objects.create(owner=owner, project=project, operation_name=operation_name, status=FocusSession.Status.RUNNING)

    @staticmethod
    def pause_session(session: FocusSession, reason: str = "manual") -> FocusSession:
        if session.status == FocusSession.Status.PAUSED or session.status == FocusSession.Status.COMPLETED:
            return session

        SessionPause.objects.create(focus_session=session, started_at=timezone.now(), reason=reason)
        session.status = FocusSession.Status.PAUSED
        session.idle_reason = reason if reason != "manual" else ""
        session.save(update_fields=["status", "idle_reason", "updated_at"])
        return session

    @staticmethod
    def pause_if_idle(session: FocusSession, now: Any | None = None) -> FocusSession:
        now = now or timezone.now()
        if session.status != FocusSession.Status.RUNNING:
            return session
        if session.last_activity_at is None:
            session.last_activity_at = now
            session.save(update_fields=["last_activity_at"])
            return session
        if (now - session.last_activity_at).total_seconds() >= 300:
            return ExecutionService.pause_session(session, reason="idle_timeout")
        return session

    @staticmethod
    def resume_session(session: FocusSession) -> FocusSession:
        if session.status != FocusSession.Status.PAUSED:
            return session
        active_pause = session.pauses.filter(ended_at__isnull=True).order_by("-started_at").first()
        if active_pause:
            active_pause.ended_at = timezone.now()
            active_pause.duration_seconds = max(0, int((active_pause.ended_at - active_pause.started_at).total_seconds()))
            active_pause.save(update_fields=["ended_at", "duration_seconds"])
            session.paused_seconds += active_pause.duration_seconds
        session.status = FocusSession.Status.RUNNING
        session.save(update_fields=["status", "paused_seconds", "updated_at"])
        return session

    @staticmethod
    @transaction.atomic
    def finish_session(session: FocusSession) -> FocusSession:
        if session.status == FocusSession.Status.COMPLETED:
            return session

        now = timezone.now()
        active_pause = session.pauses.filter(ended_at__isnull=True).order_by("-started_at").first()
        if active_pause:
            active_pause.ended_at = now
            active_pause.duration_seconds = max(0, int((active_pause.ended_at - active_pause.started_at).total_seconds()))
            active_pause.save(update_fields=["ended_at", "duration_seconds"])
            session.paused_seconds += active_pause.duration_seconds

        elapsed_seconds = max(0, int((now - session.started_at).total_seconds()))
        if session.status == FocusSession.Status.RUNNING:
            session.active_seconds += elapsed_seconds
        else:
            session.active_seconds += max(0, elapsed_seconds - session.paused_seconds)

        session.total_seconds = session.active_seconds
        session.ended_at = now
        session.status = FocusSession.Status.COMPLETED
        session.save(update_fields=["active_seconds", "paused_seconds", "total_seconds", "ended_at", "status", "updated_at"])
        return session

    @staticmethod
    def refresh_daily_summary(owner_id: int, log_date: Any) -> DailyWorkSummary:
        sessions = FocusSession.objects.filter(owner_id=owner_id, started_at__date=log_date)
        total_active_seconds = sum(session.active_seconds for session in sessions) if sessions.exists() else 0
        total_paused_seconds = sum(session.paused_seconds for session in sessions) if sessions.exists() else 0
        total_seconds = sum(session.total_seconds for session in sessions) if sessions.exists() else 0
        focus_sessions_count = sessions.count()
        average_session_seconds = int(total_seconds / focus_sessions_count) if focus_sessions_count else 0
        longest_session_seconds = max((session.total_seconds for session in sessions), default=0)
        summary, _ = DailyWorkSummary.objects.update_or_create(
            owner_id=owner_id,
            log_date=log_date,
            defaults={
                "total_active_seconds": total_active_seconds,
                "total_paused_seconds": total_paused_seconds,
                "total_seconds": total_seconds,
                "focus_sessions_count": focus_sessions_count,
                "average_session_seconds": average_session_seconds,
                "longest_session_seconds": longest_session_seconds,
            },
        )
        return summary

    @staticmethod
    def get_today_summary(owner) -> DailyWorkSummary | None:
        return DailyWorkSummary.objects.filter(owner=owner, log_date=timezone.localdate()).first()

    @staticmethod
    def build_session_payload(owner, session: FocusSession | None = None) -> dict[str, Any]:
        session = session or FocusSession.objects.filter(owner=owner, status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]).order_by("-started_at").first()
        summary = ExecutionService.get_today_summary(owner)
        return {
            "session": session,
            "summary": summary,
            "active_session_exists": session is not None,
            "hours_for_checkin": Decimal(str((summary.total_seconds if summary else 0) / 3600)).quantize(Decimal("0.01")) if summary else Decimal("0.00"),
            "focus_sessions_count": summary.focus_sessions_count if summary else 0,
            "total_active_seconds": summary.total_active_seconds if summary else 0,
            "total_active_hours": Decimal(str((summary.total_active_seconds if summary else 0) / 3600)).quantize(Decimal("0.01")) if summary else Decimal("0.00"),
            "status_label": session.get_status_display() if session else "Idle",
        }
