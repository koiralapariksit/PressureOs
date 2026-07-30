from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class PomodoroSession(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    mode = models.CharField(max_length=64, default="pomodoro")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # seconds
    interruptions = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def stop(self):
        if not self.end_time:
            self.end_time = timezone.now()
            self.duration = int((self.end_time - self.start_time).total_seconds())
            self.completed = True
            self.save()
        return self

    def add_interruption(self):
        self.interruptions = (self.interruptions or 0) + 1
        self.save()
        return self.interruptions

    def __str__(self):
        return f"PomodoroSession({self.owner}, {self.mode}, {self.start_time})"



@receiver(post_save, sender=PomodoroSession)
def _invalidate_stats_on_save(sender, instance, **kwargs):
    # Invalidate cached statistics for the owner
    try:
        uid = instance.owner_id
        cache.delete(f"stats:{uid}:weekly")
        cache.delete(f"stats:{uid}:monthly")
        cache.delete(f"stats:{uid}:lifetime")
    except Exception:
        pass


@receiver(post_delete, sender=PomodoroSession)
def _invalidate_stats_on_delete(sender, instance, **kwargs):
    try:
        uid = instance.owner_id
        cache.delete(f"stats:{uid}:weekly")
        cache.delete(f"stats:{uid}:monthly")
        cache.delete(f"stats:{uid}:lifetime")
    except Exception:
        pass
