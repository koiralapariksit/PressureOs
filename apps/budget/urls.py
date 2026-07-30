from django.urls import path

from .views import BudgetView, apply_penalty, reset_penalty

app_name = "budget"

urlpatterns = [
    path("", BudgetView.as_view(), name="index"),
    path("apply/", apply_penalty, name="apply"),
    path("reset/", reset_penalty, name="reset"),
]
