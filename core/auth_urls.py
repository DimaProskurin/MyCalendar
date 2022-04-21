from django.urls import path

from core.views import auth_views

urlpatterns = [
    path("login", auth_views.login_view),
    path("logout", auth_views.logout_view),
]
