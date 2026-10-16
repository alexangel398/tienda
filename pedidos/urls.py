from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("carrito/", views.ver_carrito, name="carrito"),
    path("carrito/agregar/<int:pk>/", views.agregar, name="agregar"),
    path("carrito/actualizar/<int:pk>/", views.actualizar, name="actualizar"),
    path("carrito/quitar/<int:pk>/", views.quitar, name="quitar"),
]