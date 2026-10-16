from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Producto

from .services import Carrito


def _cantidad(request, defecto=1):
    valor = request.POST.get("cantidad", "")
    return int(valor) if valor.isdigit() else defecto


def ver_carrito(request):
    carrito = Carrito(request)
    contexto = {"items": list(carrito), "total": carrito.total}
    return render(request, "pedidos/carrito.html", contexto)


@require_POST
def agregar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    cantidad = max(_cantidad(request), 1)
    if Carrito(request).agregar(producto, cantidad):
        messages.success(request, f"{producto.nombre} se agregó al carrito.")
    else:
        messages.error(request, f"No hay stock suficiente de {producto.nombre}.")
    return redirect("pedidos:carrito")


@require_POST
def actualizar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if not Carrito(request).actualizar(producto, _cantidad(request, 0)):
        messages.error(request, f"No hay stock suficiente de {producto.nombre}.")
    return redirect("pedidos:carrito")


@require_POST
def quitar(request, pk):
    Carrito(request).quitar(pk)
    return redirect("pedidos:carrito")

# Create your views here.
