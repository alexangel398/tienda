from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Producto

from .forms import PedidoForm
from .models import Pedido
from .services import Carrito, StockInsuficiente, crear_pedido


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


@login_required
def confirmar(request):
    carrito = Carrito(request)
    if len(carrito) == 0:
        messages.error(request, "El carrito está vacío.")
        return redirect("pedidos:carrito")

    if request.method == "POST":
        form = PedidoForm(request.POST)
        if form.is_valid():
            try:
                pedido = crear_pedido(carrito, request.user, form.cleaned_data)
            except StockInsuficiente as error:
                messages.error(
                    request,
                    "No hay stock suficiente de: "
                    + ", ".join(error.productos)
                    + ". Ajustá las cantidades.",
                )
                return redirect("pedidos:carrito")
            return redirect("pedidos:exito", pk=pedido.pk)
    else:
        form = PedidoForm()

    contexto = {"form": form, "items": list(carrito), "total": carrito.total}
    return render(request, "pedidos/confirmar.html", contexto)


@login_required
def exito(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    return render(request, "pedidos/exito.html", {"pedido": pedido})