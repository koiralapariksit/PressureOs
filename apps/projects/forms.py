from django import forms
from django.forms import ModelForm
from django.utils import timezone

from .models import Project


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "category",
            "difficulty",
            "deadline",
            "target_hours",
            "expected_daily_hours",
            "priority",
            "github_repository",
            "progress_percent",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["category", "difficulty", "priority", "status"]:
            self.fields[field_name].required = False

        self.fields["deadline"].widget = forms.TextInput(
            attrs={
                "class": "flatpickr-input w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition focus:border-gold-400 focus:ring-2 focus:ring-gold-400/30",
                "placeholder": "Choose a deadline",
                "data-flatpickr": "true",
                "data-date-format": "Y-m-d",
                "data-min-date": timezone.localdate().isoformat(),
                "autocomplete": "off",
                "readonly": True,
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ["category", "difficulty", "priority", "status"]:
            if not cleaned_data.get(field_name):
                cleaned_data[field_name] = Project._meta.get_field(field_name).default

        start_date = cleaned_data.get("start_date")
        deadline = cleaned_data.get("deadline")
        if start_date and deadline and deadline < start_date:
            raise forms.ValidationError("Deadline must be on or after the project start date.")

        return cleaned_data
