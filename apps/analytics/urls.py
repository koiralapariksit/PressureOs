from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("pressure/", views.pressure_fragment, name="pressure_fragment"),
    path("stats/", views.StatisticsView.as_view(), name="statistics"),
    path("stats/export/csv/", views.export_csv, name="statistics_export_csv"),
    path("stats/export/pdf/", views.export_pdf, name="statistics_export_pdf"),
]
 
