from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.pomodoro.models import PomodoroSession
from apps.analytics.models import Statistics


class Command(BaseCommand):
    help = "Aggregate Pomodoro sessions into user statistics (focus_time_minutes)"

    def handle(self, *args, **options):
        today = timezone.localdate()
        window_start = today - timedelta(days=1)
        users = PomodoroSession.objects.values_list('owner', flat=True).distinct()
        for uid in users:
            sessions = PomodoroSession.objects.filter(owner_id=uid, created_at__date=today)
            total_seconds = sum(s.duration or 0 for s in sessions)
            minutes = int(total_seconds // 60)
            stats, _ = Statistics.objects.get_or_create(owner_id=uid)
            # accumulate today's minutes into focus_time_minutes
            stats.focus_time_minutes = (stats.focus_time_minutes or 0) + minutes
            stats.save()
            self.stdout.write(f"Aggregated user {uid}: +{minutes} minutes")
