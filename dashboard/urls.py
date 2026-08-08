from django.urls import path

from dashboard import views

urlpatterns = [
    path("", views.home, name="home"),
    path("scrape/", views.scrape_now, name="scrape_now"),
]
