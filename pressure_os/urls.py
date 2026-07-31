"""
URL configuration for pressure_os project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('projects/', include('apps.projects.urls', namespace='projects')),
    path('budget/', include('apps.budget.urls', namespace='budget')),
    path('tracker/', include('apps.tracker.urls', namespace='tracker')),
    path('execution/', include('apps.execution.urls', namespace='execution')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('pomodoro/', include('apps.pomodoro.urls', namespace='pomodoro')),
    path('ai-judge/', include('apps.ai_judge.urls', namespace='ai_judge')),
]
