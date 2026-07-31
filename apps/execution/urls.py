from django.urls import path

from .views import ExecutionControlView, ExecutionDashboardView, FocusSessionActionView, FocusSessionCreateView

app_name = "execution"

urlpatterns = [
    path("control/", ExecutionControlView.as_view(), name="control"),
    path("panel/", ExecutionDashboardView.as_view(), name="panel"),
    path("start/", FocusSessionCreateView.as_view(), name="start"),
    path("action/", FocusSessionActionView.as_view(), name="action"),
]
