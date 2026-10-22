from django.shortcuts import render

from catalogo.models import Producto


def inicio(request):
    destacados = (
        Producto.objects.filter(stock__gt=0)
        .select_related("marca")
        .order_by("-id")[:6]
    )
    return render(request, "paginas/inicio.html", {"destacados": destacados})


def historia(request):
    return render(request, "paginas/historia.html")


def contacto(request):
    return render(request, "paginas/contacto.html")