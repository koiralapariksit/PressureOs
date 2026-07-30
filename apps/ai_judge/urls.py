from django.urls import path

from .views import AIJudgeView, refresh_ai_judge

app_name = "ai_judge"

urlpatterns = [
    path("", AIJudgeView.as_view(), name="index"),
    path("refresh/", refresh_ai_judge, name="refresh"),
]
