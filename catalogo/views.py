from django.shortcuts import render

from .models import Producto


def listado(request):
    productos = Producto.objects.select_related("categoria", "marca")
    return render(request, "catalogo/listado.html", {"productos": productos})