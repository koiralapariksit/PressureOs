from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ProjectForm
from .models import Project
from decimal import Decimal
from django.shortcuts import render
from apps.budget.models import BudgetHistory
from datetime import date


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).order_by("-updated_at")


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = "projects/form.html"
    form_class = ProjectForm
    success_url = reverse_lazy("projects:list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = "projects/form.html"
    form_class = ProjectForm
    success_url = reverse_lazy("projects:list")

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = "projects/delete_confirm.html"
    success_url = reverse_lazy("projects:list")

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


@login_required
def complete_project(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.status = Project.Status.COMPLETED
    project.progress_percent = 100
    project.is_active = False
    project.save(update_fields=["status", "progress_percent", "is_active", "updated_at"])
    return redirect("projects:list")


@login_required
def archive_project(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.is_active = False
    project.status = Project.Status.PAUSED
    project.save(update_fields=["is_active", "status", "updated_at"])
    return redirect("projects:list")


@login_required
def restart_project(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user, status=Project.Status.FAILED)
    restarted = Project.objects.create(
        owner=request.user,
        title=f"Restart: {project.title}",
        description=(project.description or "") + "\n\n[Restarted from failed project. Review scope, timeline, and milestones before you begin.]",
        category=project.category,
        difficulty=project.difficulty,
        deadline=project.deadline,
        target_hours=project.target_hours,
        expected_daily_hours=project.expected_daily_hours,
        priority=project.priority,
        github_repository=project.github_repository,
        progress_percent=0,
        status=Project.Status.ACTIVE,
        is_active=True,
    )
    return redirect("projects:edit", pk=restarted.pk)


@login_required
def hall_of_shame(request):
    """Display failed projects as a Hall of Shame with budget estimates and stats."""
    qs = Project.objects.filter(owner=request.user, status=Project.Status.FAILED).prefetch_related('failure_records')
    cards = []
    total_lost = Decimal('0')
    total_days_lost = 0
    for p in qs:
        failures = list(p.failure_records.all())
        latest = failures[0] if failures else None
        project_days_lost = sum(int(f.days_lost or 0) for f in failures) if failures else 0
        budget_lost_estimate = Decimal('0')
        for i in range(1, project_days_lost + 1):
            budget_lost_estimate += BudgetHistory.get_penalty_for_failure(i)
        total_lost += budget_lost_estimate
        total_days_lost += project_days_lost
        severity = min(
            100,
            project_days_lost * 12 + (100 - p.completion_percentage) + (10 if p.difficulty in (Project.Difficulty.HARD, Project.Difficulty.INSANE) else 0),
        )
        burn_rate = float(project_days_lost) / max(float(p.completion_percentage), 1.0)
        advice = "Review scope and restart with clearer milestones."
        if p.completion_percentage < 30:
            advice = "This project stalled early; consider archiving or relaunching smaller."
        elif p.completion_percentage < 70:
            advice = "Re-scope the remaining work and reset the plan."
        else:
            advice = "Close the failure loop and salvage the learning in the next cycle."

        cards.append({
            'project': p,
            'latest_failure': latest,
            'budget_lost_estimate': budget_lost_estimate,
            'total_days_lost': project_days_lost,
            'failure_count': len(failures),
            'severity': severity,
            'burn_rate': burn_rate,
            'advice': advice,
            'stats': {
                'completion_pct': p.completion_percentage,
                'required_hours_per_day': p.required_hours_per_day,
                'remaining_days': p.remaining_days,
                'quality': max(0, 100 - p.completion_percentage),
            }
        })

    cards.sort(key=lambda card: (card['budget_lost_estimate'], card['total_days_lost'], card['severity']), reverse=True)
    summary = {
        'count': len(cards),
        'total_lost': total_lost,
        'total_days_lost': total_days_lost,
    }

    return render(request, 'projects/hall_of_shame.html', {'cards': cards, 'summary': summary})


@login_required
def hall_of_victory(request):
    """Display completed projects with a premium layout and achievement badges."""
    qs = Project.objects.filter(owner=request.user, status=Project.Status.COMPLETED).order_by('-updated_at')
    cards = []
    for p in qs:
        completed_date = p.updated_at.date() if p.updated_at else None
        days_used = (completed_date - p.created_at.date()).days if completed_date and p.created_at else None
        on_time = False
        if completed_date and p.deadline:
            on_time = completed_date <= p.deadline
        difficulty = p.get_difficulty_display()
        achievements = []
        if on_time:
            achievements.append('On Time')
        else:
            achievements.append('Late')
        if p.difficulty in (Project.Difficulty.HARD, Project.Difficulty.INSANE):
            achievements.append('High Difficulty')
        if p.completion_percentage >= 100:
            achievements.append('Completed')
        cards.append({
            'project': p,
            'completed_date': completed_date,
            'days_used': days_used,
            'difficulty': difficulty,
            'hours': p.target_hours,
            'achievements': achievements,
            'completion_score': p.completion_percentage,
        })

    return render(request, 'projects/hall_of_victory.html', {'cards': cards})
