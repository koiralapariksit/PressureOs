from django import forms

from apps.execution.models import FocusSession


class FocusSessionForm(forms.ModelForm):
    class Meta:
        model = FocusSession
        fields = ["project", "operation_name"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=self.user).order_by("deadline")
