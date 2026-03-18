from django.urls import path
from events import views

urlpatterns = [
    path("viz/", views.viz_view, name="events_viz"),
]
