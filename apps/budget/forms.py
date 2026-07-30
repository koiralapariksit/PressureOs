from django import forms


class PenaltyTriggerForm(forms.Form):
    reason = forms.CharField(required=False, max_length=220, widget=forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"}))
