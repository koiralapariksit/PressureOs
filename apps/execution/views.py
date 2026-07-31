from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from apps.execution.forms import FocusSessionForm
from apps.execution.models import FocusSession
from apps.execution.services import ExecutionService


class ExecutionDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "execution/mission_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(ExecutionService.build_session_payload(self.request.user))
        return context


class FocusSessionCreateView(LoginRequiredMixin, FormView):
    form_class = FocusSessionForm
    template_name = "execution/mission_control.html"
    success_url = reverse_lazy("execution:control")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        project = form.cleaned_data.get("project")
        operation_name = form.cleaned_data.get("operation_name", "").strip()
        session = ExecutionService.get_or_create_active_session(self.request.user, project=project, operation_name=operation_name)
        if session.status == FocusSession.Status.COMPLETED:
            session.status = FocusSession.Status.RUNNING
            session.ended_at = None
            session.save(update_fields=["status", "ended_at", "updated_at"])
        if self.request.headers.get("HX-Request"):
            context = ExecutionService.build_session_payload(self.request.user, session=session)
            context["form"] = FocusSessionForm(user=self.request.user)
            return render(self.request, "execution/mission_panel.html", context)
        return redirect(self.success_url)


class FocusSessionActionView(LoginRequiredMixin, TemplateView):
    template_name = "execution/mission_control.html"

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        session = FocusSession.objects.filter(owner=request.user, status__in=[FocusSession.Status.RUNNING, FocusSession.Status.PAUSED]).order_by("-started_at").first()
        if not session and action != "start":
            return redirect("execution:control")

        if action == "start":
            form = FocusSessionForm(request.POST, user=request.user)
            if form.is_valid():
                project = form.cleaned_data.get("project")
                operation_name = form.cleaned_data.get("operation_name", "").strip()
                session = ExecutionService.get_or_create_active_session(request.user, project=project, operation_name=operation_name)
                if request.headers.get("HX-Request"):
                    context = ExecutionService.build_session_payload(request.user, session=session)
                    context["form"] = FocusSessionForm(user=request.user)
                    return render(request, "execution/mission_panel.html", context)
                return redirect("execution:control")
            return redirect("execution:control")

        if action == "pause":
            ExecutionService.pause_session(session)
        elif action == "resume":
            ExecutionService.resume_session(session)
        elif action == "finish":
            ExecutionService.finish_session(session)
        elif action == "end_day":
            ExecutionService.refresh_daily_summary(request.user.id, timezone.localdate())

        if request.headers.get("HX-Request"):
            context = ExecutionService.build_session_payload(request.user, session=session)
            context["form"] = FocusSessionForm(user=request.user)
            return render(request, "execution/mission_panel.html", context)
        return redirect("execution:control")


class ExecutionControlView(LoginRequiredMixin, TemplateView):
    template_name = "execution/mission_control.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(ExecutionService.build_session_payload(self.request.user))
        context["form"] = FocusSessionForm(user=self.request.user)
        return context
