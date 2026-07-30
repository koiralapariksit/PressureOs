from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.ai_judge.models import AIAnalysis
from apps.ai_judge.services import AIJudgeService
from apps.tracker.models import DailyLog


class AIJudgeView(LoginRequiredMixin, TemplateView):
    template_name = "ai_judge/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = self.request.GET.get("date")
        daily_log = None
        if today:
            daily_log = DailyLog.objects.filter(owner=self.request.user, log_date=today).order_by("-created_at").first()

        latest_log = daily_log or DailyLog.objects.filter(owner=self.request.user).order_by("-log_date").first()
        analysis_payload = AIJudgeService(self.request.user).build_analysis(daily_log=latest_log)
        analysis = None
        if latest_log:
            analysis, created = AIAnalysis.objects.update_or_create(
                owner=self.request.user,
                daily_log=latest_log,
                defaults={
                    "reality_report": analysis_payload["reality_report"],
                    "success_probability": analysis_payload["success_probability"],
                    "estimated_completion": analysis_payload["estimated_completion"],
                    "projected_failure_date": analysis_payload["projected_failure_date"],
                    "average_hours_needed": analysis_payload["required_hours_tomorrow"],
                    "recovery_plan": analysis_payload["recovery_plan"],
                    "verdict": analysis_payload["verdict"],
                },
            )

        context.update({
            "page_title": "AI Judge",
            "analysis": analysis,
            "payload": analysis_payload,
            "latest_analyses": AIAnalysis.objects.filter(owner=self.request.user).order_by("-generated_at")[:5],
        })
        return context


def refresh_ai_judge(request):
    return redirect("ai_judge:index")
