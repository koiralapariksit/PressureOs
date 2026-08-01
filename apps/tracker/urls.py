from django.urls import path

from .views import DailyCheckInView, DailyCheckInSuccessView, ProjectHoursLookupView

app_name = "tracker"

urlpatterns = [
    path("check-in/", DailyCheckInView.as_view(), name="checkin"),
    path("check-in/project-hours/", ProjectHoursLookupView.as_view(), name="project_hours"),
    path("check-in/success/", DailyCheckInSuccessView.as_view(), name="checkin_success"),
]
