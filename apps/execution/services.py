from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.execution.models import DailyWorkSummary, FocusSession, FocusSessionEvent, SessionPause
from apps.projects.models import Project


class ExecutionService:
    @staticmethod
    def format_duration(seconds: int) -> str:
        hours, remainder = divmod(max(0, int(seconds)), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def format_pomodoro_duration(seconds: int) -> str:
        minutes, remainder = divmod(max(0, int(seconds)), 60)
        return f"{minutes:02d}:{remainder:02d}"

    @staticmethod
    def get_phase_duration(session: FocusSession) -> int:
        if session.current_phase == FocusSession.Phase.SHORT_BREAK:
            return int(session.break_duration)
        if session.current_phase == FocusSession.Phase.LONG_BREAK:
            return int(session.long_break_duration)
        return int(session.work_duration)

    @staticmethod
    def get_phase_elapsed_seconds(session: FocusSession, now: Any | None = None) -> int:
        if session is None:
            return 0
        now = now or timezone.now()
        elapsed = max(0, int((now - session.phase_started_at).total_seconds())) if session.phase_started_at else 0
        pause_delta = 0
        for pause in session.pauses.all():
            overlap_start = max(session.phase_started_at, pause.started_at)
            overlap_end = min(now, pause.ended_at or now)
            if overlap_end > overlap_start:
                pause_delta += max(0, int((overlap_end - overlap_start).total_seconds()))
        return max(0, elapsed - pause_delta)

    @staticmethod
    def get_pomodoro_remaining_seconds(session: FocusSession | None, now: Any | None = None) -> int:
        if session is None:
            return 0
        phase_duration = ExecutionService.get_phase_duration(session)
        phase_elapsed = ExecutionService.get_phase_elapsed_seconds(session, now=now)
        return max(0, phase_duration - phase_elapsed)

    @staticmethod
    def build_pomodoro_state(session: FocusSession | None, now: Any | None = None) -> dict[str, Any]:
        now = now or timezone.now()
        if session is None:
            return {
                "phase": FocusSession.Phase.WORK,
                "phase_label": "Work Session",
                "remaining_seconds": 1500,
                "remaining_display": "25:00",
                "work_duration": 1500,
                "break_duration": 300,
                "long_break_duration": 900,
                "long_break_every": 4,
                "cycle_number": 1,
                "completed_cycles": 0,
                "interruptions": 0,
                "estimated_remaining_cycles": 4,
                "focus_efficiency": 0,
                "phase_started_at": now,
                "phase_display": "Work",
                "phase_progress": 0,
                "phase_total_seconds": 1500,
            }

        remaining_seconds = ExecutionService.get_pomodoro_remaining_seconds(session, now=now)
        phase_title = {
            FocusSession.Phase.WORK: "Work Session",
            FocusSession.Phase.SHORT_BREAK: "Short Break",
            FocusSession.Phase.LONG_BREAK: "Long Break",
        }.get(session.current_phase, "Work Session")
        estimated_remaining_cycles = max(0, int(session.long_break_every - (session.completed_cycles % session.long_break_every))) if session.long_break_every else 0
        elapsed = ExecutionService.get_phase_elapsed_seconds(session, now=now)
        phase_total_seconds = ExecutionService.get_phase_duration(session)
        phase_progress = int((elapsed / max(1, phase_total_seconds)) * 100)
        return {
            "phase": session.current_phase,
            "phase_label": phase_title,
            "remaining_seconds": remaining_seconds,
            "remaining_display": ExecutionService.format_pomodoro_duration(remaining_seconds),
            "work_duration": int(session.work_duration),
            "break_duration": int(session.break_duration),
            "long_break_duration": int(session.long_break_duration),
            "long_break_every": int(session.long_break_every),
            "cycle_number": int(session.cycle_number),
            "completed_cycles": int(session.completed_cycles),
            "interruptions": int(session.interruptions),
            "estimated_remaining_cycles": estimated_remaining_cycles,
            "focus_efficiency": round((session.completed_cycles / max(1, session.cycle_number)) * 100) if session.cycle_number else 0,
            "phase_started_at": session.phase_started_at,
            "phase_elapsed_seconds": elapsed,
            "phase_display": phase_title,
            "phase_progress": min(100, phase_progress),
            "phase_total_seconds": phase_total_seconds,
        }

    @staticmethod
    def record_interrupt(session: FocusSession) -> FocusSession:
        if session is None:
            return session
        session.interruptions += 1
        session.last_activity_at = timezone.now()
        session.save(update_fields=["interruptions", "last_activity_at", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="interrupt",
            label="Interrupted",
            detail="Mission interrupted and timeline updated.",
        )
        return session

    @staticmethod
    def skip_break(session: FocusSession) -> FocusSession:
        if session is None:
            return session
        session.current_phase = FocusSession.Phase.WORK
        session.phase_started_at = timezone.now()
        session.last_activity_at = timezone.now()
        session.save(update_fields=["current_phase", "phase_started_at", "last_activity_at", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="pomodoro",
            label="Break skipped",
            detail="The next work cycle has been resumed immediately.",
        )
        return session

    @staticmethod
    def reset_pomodoro(session: FocusSession) -> FocusSession:
        if session is None:
            return session
        session.current_phase = FocusSession.Phase.WORK
        session.cycle_number = 1
        session.completed_cycles = 0
        session.phase_started_at = timezone.now()
        session.last_activity_at = timezone.now()
        session.save(update_fields=["current_phase", "cycle_number", "completed_cycles", "phase_started_at", "last_activity_at", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="pomodoro",
            label="Cycle reset",
            detail="The Pomodoro engine restarted the mission cycle from the top.",
        )
        return session

    @staticmethod
    def advance_pomodoro_phase(session: FocusSession, now: Any | None = None) -> FocusSession:
        now = now or timezone.now()
        if session.status != FocusSession.Status.RUNNING:
            return session
        remaining_seconds = ExecutionService.get_pomodoro_remaining_seconds(session, now=now)
        if remaining_seconds > 0:
            return session

        if session.current_phase == FocusSession.Phase.WORK:
            if session.completed_cycles % session.long_break_every == 0:
                session.current_phase = FocusSession.Phase.LONG_BREAK
                detail = "Long break has begun."
            else:
                session.current_phase = FocusSession.Phase.SHORT_BREAK
                detail = "Short break has begun."
            FocusSessionEvent.objects.create(
                focus_session=session,
                kind="pomodoro",
                label="Pomodoro completed",
                detail=detail,
            )
        elif session.current_phase == FocusSession.Phase.SHORT_BREAK:
            session.current_phase = FocusSession.Phase.WORK
            session.completed_cycles += 1
            session.cycle_number += 1
            FocusSessionEvent.objects.create(
                focus_session=session,
                kind="pomodoro",
                label="Short break finished",
                detail="Next work session started after confirmation.",
            )
        elif session.current_phase == FocusSession.Phase.LONG_BREAK:
            session.current_phase = FocusSession.Phase.WORK
            session.completed_cycles += 1
            session.cycle_number += 1
            FocusSessionEvent.objects.create(
                focus_session=session,
                kind="pomodoro",
                label="Long break finished",
                detail="Long break finished, next work block is ready.",
            )

        session.phase_started_at = now
        session.last_activity_at = now
        session.save(update_fields=["completed_cycles", "cycle_number", "current_phase", "phase_started_at", "last_activity_at", "updated_at"])
        return session

    @staticmethod
    def get_elapsed_seconds(session: FocusSession | None, now: Any | None = None) -> int:
        if session is None:
            return 0
        if session.status == FocusSession.Status.COMPLETED:
            return session.total_seconds

        now = now or timezone.now()
        elapsed = max(0, int((now - session.started_at).total_seconds()))
        open_pause_seconds = 0
        if session.status == FocusSession.Status.PAUSED:
            pause = session.pauses.filter(ended_at__isnull=True).order_by("-started_at").first()
            if pause:
                open_pause_seconds = max(0, int((now - pause.started_at).total_seconds()))
        return max(0, session.active_seconds + elapsed - session.paused_seconds - open_pause_seconds)

    @staticmethod
    def get_control_state(session: FocusSession | None) -> dict[str, bool]:
        if session is None:
            return {"can_start": True, "can_pause": False, "can_resume": False, "can_finish": False, "can_abort": False}
        if session.status == FocusSession.Status.RUNNING:
            return {"can_start": False, "can_pause": True, "can_resume": False, "can_finish": True, "can_abort": True}
        if session.status == FocusSession.Status.PAUSED:
            return {"can_start": False, "can_pause": False, "can_resume": True, "can_finish": True, "can_abort": True}
        return {"can_start": True, "can_pause": False, "can_resume": False, "can_finish": False, "can_abort": False}

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

        session = FocusSession.objects.create(owner=owner, project=project, operation_name=operation_name, status=FocusSession.Status.RUNNING)
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="mission",
            label="Mission started",
            detail=operation_name or "Focus operation",
        )
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="pomodoro",
            label="Pomodoro started",
            detail="Work phase is live.",
        )
        return session

    @staticmethod
    def pause_session(session: FocusSession, reason: str = "manual") -> FocusSession:
        if session.status != FocusSession.Status.RUNNING:
            return session

        SessionPause.objects.create(focus_session=session, started_at=timezone.now(), reason=reason)
        session.status = FocusSession.Status.PAUSED
        session.idle_reason = reason if reason != "manual" else ""
        session.save(update_fields=["status", "idle_reason", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="pause",
            label="Paused",
            detail=reason or "Manual pause",
        )
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
    @transaction.atomic
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
        session.last_activity_at = timezone.now()
        session.save(update_fields=["status", "paused_seconds", "last_activity_at", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="resume",
            label="Resumed",
            detail="Mission re-entered the live execution lane.",
        )
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

        session.active_seconds = ExecutionService.get_elapsed_seconds(session, now=now)
        session.total_seconds = session.active_seconds
        session.ended_at = now
        session.status = FocusSession.Status.COMPLETED
        session.save(update_fields=["active_seconds", "paused_seconds", "total_seconds", "ended_at", "status", "updated_at"])
        FocusSessionEvent.objects.create(
            focus_session=session,
            kind="mission",
            label="Mission finished",
            detail=session.operation_name or "Focus operation",
        )
        return session

    @staticmethod
    @transaction.atomic
    def abort_session(session: FocusSession) -> FocusSession:
        if session.status in [FocusSession.Status.COMPLETED, FocusSession.Status.ABORTED]:
            return session
        now = timezone.now()
        active_pause = session.pauses.filter(ended_at__isnull=True).order_by("-started_at").first()
        if active_pause:
            active_pause.ended_at = now
            active_pause.duration_seconds = max(0, int((now - active_pause.started_at).total_seconds()))
            active_pause.save(update_fields=["ended_at", "duration_seconds"])
            session.paused_seconds += active_pause.duration_seconds
        session.active_seconds = ExecutionService.get_elapsed_seconds(session, now=now)
        session.total_seconds = session.active_seconds
        session.ended_at = now
        session.status = FocusSession.Status.ABORTED
        session.save(update_fields=["active_seconds", "total_seconds", "paused_seconds", "ended_at", "status", "updated_at"])
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
    def get_project_hours_for_today(owner, project: Project | None) -> Decimal:
        if project is None:
            return Decimal("0.00")
        sessions = FocusSession.objects.filter(
            owner=owner,
            project=project,
            started_at__date=timezone.localdate(),
            status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED, FocusSession.Status.COMPLETED],
        )
        total_seconds = sum(ExecutionService.get_elapsed_seconds(session) for session in sessions)
        return Decimal(str(total_seconds / 3600)).quantize(Decimal("0.01"))

    @staticmethod
    def build_session_payload(owner, session: FocusSession | None = None) -> dict[str, Any]:
        filtered_session = session or FocusSession.objects.filter(owner=owner, status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]).order_by("-started_at").first()
        if filtered_session and filtered_session.status not in [FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]:
            filtered_session = None

        if filtered_session and filtered_session.status == FocusSession.Status.RUNNING:
            filtered_session = ExecutionService.advance_pomodoro_phase(filtered_session)

        summary = ExecutionService.get_today_summary(owner)
        elapsed_seconds = ExecutionService.get_elapsed_seconds(filtered_session)
        live_metrics = ExecutionService.build_live_metrics(owner)
        payload = {
            "session": filtered_session,
            "summary": summary,
            "active_session_exists": filtered_session is not None,
            "hours_for_checkin": Decimal(str((summary.total_seconds if summary else 0) / 3600)).quantize(Decimal("0.01")) if summary else Decimal("0.00"),
            "focus_sessions_count": summary.focus_sessions_count if summary else 0,
            "total_active_seconds": summary.total_active_seconds if summary else 0,
            "total_active_hours": Decimal(str((summary.total_active_seconds if summary else 0) / 3600)).quantize(Decimal("0.01")) if summary else Decimal("0.00"),
            "status_label": filtered_session.get_status_display() if filtered_session else "Idle",
            "elapsed_seconds": elapsed_seconds,
            "elapsed_display": ExecutionService.format_duration(elapsed_seconds),
            "control_state": ExecutionService.get_control_state(filtered_session),
            "live_metrics": live_metrics,
            "pomodoro": ExecutionService.build_pomodoro_state(filtered_session),
        }
        payload.update(ExecutionService.build_operational_context(owner, session=filtered_session))
        return payload

    @staticmethod
    def build_live_metrics(owner) -> dict[str, Any]:
        today = timezone.localdate()
        sessions = list(
            FocusSession.objects.filter(owner=owner, started_at__date=today)
            .select_related("project")
            .prefetch_related("pauses")
        )
        active_seconds = sum(ExecutionService.get_elapsed_seconds(session) for session in sessions if session.status in [FocusSession.Status.RUNNING, FocusSession.Status.PAUSED])
        completed_seconds = sum(session.total_seconds for session in sessions if session.status == FocusSession.Status.COMPLETED)
        focus_seconds = active_seconds + completed_seconds
        completed_sessions = [session for session in sessions if session.status == FocusSession.Status.COMPLETED]
        total_sessions = len(completed_sessions)
        average_seconds = int(sum(session.total_seconds for session in completed_sessions) / total_sessions) if total_sessions else 0
        longest_seconds = max((session.total_seconds for session in completed_sessions), default=0)
        paused_seconds = sum(session.paused_seconds for session in sessions)
        interruptions = sum(session.interruptions for session in sessions)
        completed_cycles = sum(session.completed_cycles for session in sessions)
        denominator = focus_seconds + paused_seconds
        return {
            "focus_seconds": focus_seconds,
            "focus_display": ExecutionService.format_duration(focus_seconds),
            "paused_seconds": paused_seconds,
            "paused_display": ExecutionService.format_duration(paused_seconds),
            "completed_sessions": total_sessions,
            "average_display": ExecutionService.format_duration(average_seconds),
            "longest_display": ExecutionService.format_duration(longest_seconds),
            "deep_work_percent": round((focus_seconds / denominator) * 100) if denominator else 0,
            "interruptions": interruptions,
            "completed_cycles": completed_cycles,
            "focus_ratio": round((focus_seconds / max(1, focus_seconds + paused_seconds)) * 100) if focus_seconds + paused_seconds else 0,
        }

    @staticmethod
    def build_operational_context(owner, session: FocusSession | None = None) -> dict[str, Any]:
        session = session or FocusSession.objects.filter(owner=owner, status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]).order_by("-started_at").first()
        summary = ExecutionService.get_today_summary(owner)
        projects = Project.objects.filter(owner=owner, is_active=True).order_by("deadline")[:6]
        timeline = []
        if session:
            timeline.append({"kind": "start", "label": "Mission started", "detail": session.operation_name or "Focus operation", "time": session.started_at})
            for pause in session.pauses.all():
                timeline.append({"kind": "pause", "label": "Paused", "detail": pause.reason or "Pause", "time": pause.started_at})
            for event in session.events.all():
                timeline.append({"kind": event.kind, "label": event.label, "detail": event.detail, "time": event.created_at})
        if summary:
            timeline.append({"kind": "summary", "label": "Daily summary", "detail": f"{summary.total_seconds // 3600}h tracked", "time": timezone.now()})
        timeline.sort(key=lambda item: item["time"], reverse=True)

        reality_facts = []
        if summary:
            reality_facts.append(f"Today contains {summary.total_seconds // 3600}h of tracked execution.")
            reality_facts.append(f"Average session length is {summary.average_session_seconds // 60 if summary.average_session_seconds else 0} minutes.")
            reality_facts.append(f"The longest session reached {summary.longest_session_seconds // 60 if summary.longest_session_seconds else 0} minutes.")
        else:
            reality_facts.append("No execution data has been logged for today yet.")
            reality_facts.append("Start a mission to create the first operational record.")
            reality_facts.append("Idle time will be surfaced once the session is active.")

        mission_map = []
        for project in projects:
            pressure = project.pressure_level
            mission_map.append({
                "title": project.title,
                "deadline": project.deadline,
                "pressure": pressure,
                "days_remaining": project.days_remaining,
                "completion_percent": project.progress_percent,
                "dependency": "None" if project.priority != "critical" else "Critical path",
                "risk": "Low" if project.progress_percent >= 70 else "Watch",
            })

        return {
            "timeline": timeline,
            "reality_facts": reality_facts,
            "mission_map": mission_map,
            "pressure_level": session.project.pressure_level if session and session.project else "Stable",
            "pressure_score": 72 if session else 58,
            "execution_score": 88 if summary and summary.total_seconds else 74,
            "consistency_score": 83 if summary else 69,
        }
