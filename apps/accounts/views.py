from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import CustomAuthenticationForm, CustomPasswordResetForm, CustomUserCreationForm
from .models import Profile


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomAuthenticationForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")
        if remember_me:
            self.request.session.set_expiry(1209600)
        else:
            self.request.session.set_expiry(0)
        login(self.request, form.get_user())
        messages.success(self.request, "You are inside the system.")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "The username or password you entered is incorrect.")
        return super().form_invalid(form)


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("core:home")
    http_method_names = ["get", "post", "options", "head"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in {"get", "post"}:
            return self.get(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been signed out.")
        return redirect(self.get_default_redirect_url())


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Account created. The pressure begins now.")
        return super().form_valid(form)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "registration/password_reset.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")
    form_class = CustomPasswordResetForm

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "If the email matches an account, reset instructions were sent.")
        return response


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    fields = ["avatar", "bio", "wake_time", "budget"]
    template_name = "registration/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


