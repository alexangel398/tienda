from django.urls import path

from . import views

app_name = "paginas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    
    path("contacto/", views.contacto, name="contacto"),
    path("health/", views.salud, name="salud"),
]