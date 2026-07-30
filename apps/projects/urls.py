from django.urls import path

from .views import (
    ProjectCreateView,
    ProjectDeleteView,
    ProjectListView,
    ProjectUpdateView,
    archive_project,
    complete_project,
    hall_of_shame,
    hall_of_victory,
    restart_project,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListView.as_view(), name="list"),
    path("new/", ProjectCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", ProjectUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", ProjectDeleteView.as_view(), name="delete"),
    path("<int:pk>/complete/", complete_project, name="complete"),
    path("<int:pk>/archive/", archive_project, name="archive"),
    path("<int:pk>/restart/", restart_project, name="restart"),
    path("hall-of-shame/", hall_of_shame, name="hall_of_shame"),
    path("hall-of-victory/", hall_of_victory, name="hall_of_victory"),
]
