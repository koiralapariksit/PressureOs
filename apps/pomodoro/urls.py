from django.urls import path
from . import views

app_name = "pomodoro"

urlpatterns = [
    path("timer/", views.timer_view, name="timer"),
    path("api/start/", views.start_session, name="start_session"),
    path("api/stop/", views.stop_session, name="stop_session"),
    path("api/interrupt/", views.record_interrupt, name="record_interrupt"),
    path("api/daily/", views.daily_totals, name="daily_totals"),
]
