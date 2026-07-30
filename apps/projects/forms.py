from django.forms import ModelForm

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

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ["category", "difficulty", "priority", "status"]:
            if not cleaned_data.get(field_name):
                cleaned_data[field_name] = Project._meta.get_field(field_name).default
        return cleaned_data
