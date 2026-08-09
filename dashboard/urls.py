from django.urls import path

from dashboard import views

urlpatterns = [
    path("", views.home, name="home"),
    path("trends/", views.trends, name="trends"),
    path("distribution/", views.distribution, name="distribution"),
]
