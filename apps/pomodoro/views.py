import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import PomodoroSession
from apps.analytics.models import Statistics
from apps.analytics.services import award_achievement, award_xp


@login_required
def timer_view(request):
    return render(request, "pomodoro/timer.html")


@require_POST
@login_required
def start_session(request):
    allowed_modes = {"pomodoro", "focus", "short_break", "long_break"}
    mode = request.POST.get("mode", "pomodoro")
    mode = mode.strip().lower() if isinstance(mode, str) else "pomodoro"
    if mode not in allowed_modes:
        mode = "pomodoro"
    session = PomodoroSession.objects.create(owner=request.user, mode=mode)
    return JsonResponse({"id": session.id, "start_time": session.start_time.isoformat()})


@require_POST
@login_required
def stop_session(request):
    sid = request.POST.get("id")
    if not sid:
        return HttpResponseBadRequest("Missing id")
    session = get_object_or_404(PomodoroSession, id=sid, owner=request.user)
    if session.end_time:
        return JsonResponse({"status": "already_stopped"})
    session.stop()
    # Update statistics focus_time_minutes immediately for today's session and award gamification progress.
    try:
        minutes = int((session.duration or 0) // 60)
        stats, _ = Statistics.objects.get_or_create(owner=request.user)
        stats.focus_time_minutes = (stats.focus_time_minutes or 0) + minutes
        stats.save(update_fields=["focus_time_minutes"])

        award_xp(request.user, min(50, max(5, minutes * 5)), request=request)
        if session.mode == "pomodoro":
            award_achievement(request.user, "FIRST_SESSION", request=request)
        if minutes >= 25 and session.completed:
            award_achievement(request.user, "FOCUS_FLOW", details="Completed a full Pomodoro session.", request=request)
        if minutes >= 50:
            award_achievement(request.user, "FULL_THROTTLE", details="Earned after an extended focus session.", request=request)
    except Exception:
        pass
    return JsonResponse({"id": session.id, "duration": session.duration})


@require_POST
@login_required
def record_interrupt(request):
    sid = request.POST.get("id")
    if not sid:
        return HttpResponseBadRequest("Missing id")
    session = get_object_or_404(PomodoroSession, id=sid, owner=request.user)
    interruptions = session.add_interruption()
    return JsonResponse({"interruptions": interruptions})


@login_required
def daily_totals(request):
    user = request.user
    today = timezone.localdate()
    sessions = PomodoroSession.objects.filter(owner=user, created_at__date=today)
    total_seconds = sum((s.duration or 0) for s in sessions)
    completed = sessions.filter(completed=True).count()
    interruptions = sum(s.interruptions or 0 for s in sessions)

    focus_score = 0
    if completed > 0:
        focus_score = int(max(0, 100 * (completed / (completed + interruptions))))

    return JsonResponse({
        "date": str(today),
        "total_seconds": total_seconds,
        "completed": completed,
        "interruptions": interruptions,
        "focus_score": focus_score,
    })
