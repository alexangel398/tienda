from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.listado, name="listado"),
    path("producto/<int:pk>/", views.detalle, name="detalle"),
]