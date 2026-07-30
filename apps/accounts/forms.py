from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"})
    )
    remember_me = forms.BooleanField(required=False, label="Remember me", widget=forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-white/20 bg-black/40"}))


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email", widget=forms.EmailInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}))
    first_name = forms.CharField(required=True, label="First name", widget=forms.TextInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}))
    last_name = forms.CharField(required=True, label="Last name", widget=forms.TextInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}),
            "password1": forms.PasswordInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}),
            "password2": forms.PasswordInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"}),
        }


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none ring-0 focus:border-gold-400"})
    )
