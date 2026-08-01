from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView, View

from apps.ai_judge.services import AIJudgeService
from apps.analytics.models import Achievement, Statistics
from apps.analytics.services import award_achievement, award_xp, build_pressure_state
from apps.budget.models import BudgetHistory
from apps.execution.services import ExecutionService
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog


class DailyCheckInForm(ModelForm):
    class Meta:
        model = DailyLog
        fields = [
            "project",
            "hours_worked",
            "tasks_finished",
            "notes",
            "energy_level",
            "github_commits",
            "distractions",
            "screenshot_proof",
            "completed",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["project"].queryset = Project.objects.filter(owner=self.user).order_by("deadline")
            self.fields["project"].widget.attrs.update({
                "hx-get": reverse_lazy("tracker:project_hours"),
                "hx-target": "#id_hours_worked",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
            })
        self.fields["completed"].required = False
        self.fields["hours_worked"].required = False
        self.fields["hours_worked"].initial = Decimal("0.00")
        self.fields["hours_worked"].widget.attrs["min"] = "0"
        self.fields["hours_worked"].widget.attrs["step"] = "0.01"


class DailyCheckInView(LoginRequiredMixin, FormView):
    template_name = "tracker/checkin.html"
    form_class = DailyCheckInForm
    success_url = reverse_lazy("tracker:checkin_success")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        project = form.cleaned_data["project"]
        lookup_kwargs = {
            "owner": self.request.user,
            "project": project,
            "log_date": timezone.localdate(),
        }
        hours_worked = form.cleaned_data.get("hours_worked")
        if hours_worked in {None, ""}:
            hours_worked = ExecutionService.get_project_hours_for_today(self.request.user, project)
        defaults = {
            "hours_worked": hours_worked or Decimal("0.00"),
            "tasks_finished": form.cleaned_data["tasks_finished"],
            "notes": form.cleaned_data["notes"],
            "energy_level": form.cleaned_data["energy_level"],
            "github_commits": form.cleaned_data["github_commits"],
            "distractions": form.cleaned_data["distractions"],
            "completed": form.cleaned_data["completed"],
        }

        screenshot = form.cleaned_data.get("screenshot_proof")
        if screenshot is not None:
            defaults["screenshot_proof"] = screenshot

        daily_log, _ = DailyLog.objects.update_or_create(
            defaults=defaults,
            **lookup_kwargs,
        )
        self._refresh_statistics_and_budget()
        return super().form_valid(form)

    def _refresh_statistics_and_budget(self):
        owner = self.request.user
        logs = DailyLog.objects.filter(owner=owner)
        total_hours = sum((entry.hours_worked or Decimal("0")) for entry in logs) if logs.exists() else Decimal("0")
        completed_logs = logs.filter(completed=True).count()
        total_logs = logs.count()
        success_percentage = int((completed_logs / total_logs * 100) if total_logs else 0)
        latest_budget = BudgetHistory.objects.filter(owner=owner).order_by("-created_at").first()
        initial_budget = BudgetHistory.get_or_create_initial_entry(owner)
        current_budget = latest_budget.remaining_budget if latest_budget else initial_budget.amount
        stats, _ = Statistics.objects.get_or_create(owner=owner)
        stats.hours_total = total_hours
        stats.success_percentage = success_percentage
        stats.budget_remaining = current_budget
        stats.commits = sum(entry.github_commits for entry in logs)
        pressure_state = build_pressure_state(owner)
        stats.pressure_level = pressure_state["score"]
        stats.save(update_fields=["hours_total", "success_percentage", "budget_remaining", "commits", "pressure_level", "updated_at"])

        xp_reward = int(total_hours * 10) + (5 if completed_logs > 0 else 0)
        award_xp(owner, xp_reward)

        if completed_logs == total_logs and total_logs > 0:
            award_achievement(owner, "PROJECT_ARCHITECT", details="Perfect daily check-in consistency.")
        if success_percentage >= 90:
            award_achievement(owner, "HALL_OF_VICTORY", details="High success streak.")

        if total_logs and completed_logs < total_logs:
            failure_count = total_logs - completed_logs
            BudgetHistory.apply_penalty(owner, failure_count, reason="Daily check-in missed")
        elif total_logs and completed_logs == total_logs:
            BudgetHistory.reset_budget(owner, reason="Successful day")


class ProjectHoursLookupView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project_id = request.GET.get("project")
        project = None
        if project_id:
            project = Project.objects.filter(owner=request.user, pk=project_id).first()
        hours_value = ExecutionService.get_project_hours_for_today(request.user, project)
        html = render_to_string(
            "tracker/partials/project_hours_field.html",
            {
                "hours_value": hours_value,
                "form": DailyCheckInForm(user=request.user),
            },
        )
        return HttpResponse(html)


class DailyCheckInSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "tracker/checkin_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_log = DailyLog.objects.filter(owner=self.request.user).order_by("-log_date", "-created_at").first()
        context.update({
            "page_title": "Daily Check-in",
            "latest_log": latest_log,
            "analysis": AIJudgeService(self.request.user).build_analysis(daily_log=latest_log),
        })
        return context
