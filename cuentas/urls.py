from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", LoginView.as_view(template_name="cuentas/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]