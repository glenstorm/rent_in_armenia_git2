from django.urls import path

from dashboard import views

urlpatterns = [
    path("", views.home, name="home"),
    path("trends/", views.trends, name="trends"),
    path("distribution/", views.distribution, name="distribution"),
    path("tavush-houses/", views.tavush_houses, name="tavush_houses"),
    path("dilijan-houses/", views.dilijan_houses, name="dilijan_houses"),
    path("verify/", views.bot_verify, name="bot_verify"),
    path("verify/captcha.svg", views.bot_captcha_image, name="bot_captcha_image"),
]
