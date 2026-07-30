from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from .forms import PenaltyTriggerForm
from .models import BudgetHistory


class BudgetView(LoginRequiredMixin, TemplateView):
    template_name = "budget/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        history = BudgetHistory.objects.filter(owner=self.request.user).order_by("-created_at")
        latest = history.first()
        initial_entry = BudgetHistory.get_or_create_initial_entry(self.request.user)

        context.update({
            "page_title": "Punishment Ledger",
            "initial_budget": initial_entry.amount,
            "current_budget": latest.remaining_budget if latest else initial_entry.amount,
            "money_lost": max(initial_entry.amount - (latest.remaining_budget if latest else initial_entry.amount), Decimal("0")),
            "history": history[:10],
            "form": PenaltyTriggerForm(),
        })
        return context


def apply_penalty(request):
    if request.method == "POST":
        form = PenaltyTriggerForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get("reason") or "Daily failure"
            failure_count = BudgetHistory.objects.filter(owner=request.user, change_type=BudgetHistory.ChangeType.DEDUCTION).count() + 1
            BudgetHistory.apply_penalty(request.user, failure_count, reason=reason)
    return redirect("budget:index")


def reset_penalty(request):
    BudgetHistory.reset_budget(request.user, reason="Successful day")
    return redirect("budget:index")
