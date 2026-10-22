from django.urls import path

from . import views

app_name = "paginas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("historia/", views.historia, name="historia"),
    path("contacto/", views.contacto, name="contacto"),
]