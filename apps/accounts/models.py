from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/%Y/%m/%d/", blank=True, null=True)
    bio = models.TextField(blank=True)
    wake_time = models.TimeField(blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=12000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        return f"{self.user.username}'s profile"
