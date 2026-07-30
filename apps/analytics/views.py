from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from io import StringIO

from .services import build_pressure_state

from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.budget.models import BudgetHistory
from apps.projects.models import FailureRecord, Project
from apps.tracker.models import DailyLog
from apps.analytics.models import Statistics


class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/statistics.html"

    def _date_range(self, days: int):
        end = timezone.localdate()
        start = end - timedelta(days=days - 1)
        return start, end

    def _build_daily_series(self, owner, days: int):
        start, end = self._date_range(days)
        labels = []
        series = []
        for i in range(days):
            day = start + timedelta(days=i)
            labels.append(day.strftime("%b %d"))
            total = (
                DailyLog.objects.filter(owner=owner, log_date=day).aggregate(total=Sum("hours_worked"))["total"]
                or 0
            )
            series.append(float(total))
        return labels, series

    def _build_monthly_series(self, owner, months: int = 12):
        today = timezone.localdate()
        labels = []
        series = []
        # iterate backward from months-1 to 0 to produce oldest->newest
        for i in range(months - 1, -1, -1):
            target = (today.replace(day=1) - timedelta(days=30 * i))
            year = target.year
            month_no = target.month
            labels.append(f"{target.strftime('%b %Y')}")
            total = (
                DailyLog.objects.filter(owner=owner, log_date__year=year, log_date__month=month_no)
                .aggregate(total=Sum("hours_worked"))["total"]
                or 0
            )
            series.append(float(total))
        return labels, series

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Hours series
        weekly_labels, weekly_hours = self._build_daily_series(user, 7)
        monthly_labels, monthly_hours = self._build_daily_series(user, 30)

        stats = Statistics.objects.filter(owner=user).first()
        failures = FailureRecord.objects.filter(project__owner=user).count()

        # Budget history series (last 12 entries)
        budget_entries = BudgetHistory.objects.filter(owner=user).order_by("-created_at")[:12]
        budget_entries = list(budget_entries)[::-1]
        budget_labels = [e.created_at.strftime("%b %d") for e in budget_entries]
        budget_series = [float(e.remaining_budget) for e in budget_entries]

        projects = list(Project.objects.filter(owner=user).values("title", "progress_percent")[:10])

        payload = {
            "page_title": "Statistics",
            "weekly_labels": weekly_labels,
            "weekly_hours": weekly_hours,
            "monthly_labels": monthly_labels,
            "monthly_hours": monthly_hours,
            "lifetime_hours": float(stats.hours_total) if stats else 0,
            "failures": failures,
            "budget_labels": budget_labels,
            "budget_series": budget_series,
            "consistency": int(stats.success_percentage if stats else 0),
            "focus_hours": round((stats.focus_time_minutes / 60) if stats else 0, 1),
            "projects": projects,
            "avg_progress": int(sum(p["progress_percent"] for p in projects) / len(projects)) if projects else 0,
            "pressure": int(stats.pressure_level if stats else 0),
        }

        # allow interactive range selection
        selected_range = self.request.GET.get("range", "weekly")
        cache_key = f"stats:{user.id}:{selected_range}"
        cached = cache.get(cache_key)
        if cached:
            context.update(cached)
            return context

        if selected_range == "weekly":
            labels = weekly_labels
            hours = weekly_hours
        elif selected_range == "monthly":
            labels = monthly_labels
            hours = monthly_hours
        else:
            labels, hours = self._build_monthly_series(user, 12)

        payload.update({
            "labels": labels,
            "hours": hours,
            "selected_range": selected_range,
        })

        cache.set(cache_key, payload, timeout=60)
        context.update(payload)
        return context


@login_required
def pressure_fragment(request):
    """Return a small fragment showing the current pressure pill and animated meter.

    This endpoint is polled by HTMX from the dashboard to keep the UI live.
    """
    state = build_pressure_state(request.user)
    context = {
        "pressure_label": state["label"],
        "pressure_description": state["description"],
        "pressure_pill_class": state["pill_class"],
        "pressure_panel_class": state["panel_class"],
        "pressure_accent_class": state["accent_class"],
        "score": state["score"],
    }
    return render(request, "analytics/pressure_fragment.html", context)
    

@login_required
def export_csv(request):
    owner = request.user
    selected_range = request.GET.get("range", "weekly")
    svc = StatisticsView()
    if selected_range == "weekly":
        labels, series = svc._build_daily_series(owner, 7)
    elif selected_range == "monthly":
        labels, series = svc._build_daily_series(owner, 30)
    else:
        labels, series = svc._build_monthly_series(owner, 12)

    output = StringIO()
    output.write("label,value\n")
    for l, v in zip(labels, series):
        output.write(f"{l},{v}\n")

    resp = HttpResponse(output.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename=statistics_{selected_range}.csv"
    return resp


@login_required
def export_pdf(request):
    owner = request.user
    selected_range = request.GET.get("range", "weekly")
    svc = StatisticsView()
    if selected_range == "weekly":
        labels, series = svc._build_daily_series(owner, 7)
    elif selected_range == "monthly":
        labels, series = svc._build_daily_series(owner, 30)
    else:
        labels, series = svc._build_monthly_series(owner, 12)

    # Try generating a PDF via reportlab if available
    # Generate a styled PDF using reportlab
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"Statistics report — Range: {selected_range}", styles['Heading2']))
    story.append(Spacer(1, 12))

    # Add a small table of label/value
    table_data = [["Label", "Value"]]
    for l, v in zip(labels, series):
        table_data.append([str(l), str(v)])

    t = Table(table_data, colWidths=[300, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#374151')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#0b1220'), colors.HexColor('#061020')])
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Summary
    story.append(Paragraph(f"Lifetime hours: {payload.get('lifetime_hours', 0)}", styles['Normal']))
    story.append(Paragraph(f"Failures: {payload.get('failures', 0)}", styles['Normal']))
    story.append(Paragraph(f"Consistency: {payload.get('consistency', 0)}%", styles['Normal']))
    story.append(Paragraph(f"Focus score (minutes): {payload.get('focus_hours', 0)}h", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    resp = HttpResponse(buffer.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename=statistics_{selected_range}.pdf'
    return resp
