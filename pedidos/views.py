from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.conf import settings
from catalogo.models import Color, Producto

from .forms import PedidoForm
from .models import Pedido
from .services import Carrito, StockInsuficiente, crear_pedido, mensaje_pedido, url_whatsapp, CarritoInvalido

def _colores(request):
    """Colores tildados en la ficha, sin repetir y ordenados por nombre."""
    ids = {int(v) for v in request.POST.getlist("colores") if v.isdigit()}
    return list(Color.objects.filter(pk__in=ids))

def _color(request):
    valor = request.POST.get("color", "")
    return Color.objects.filter(pk=int(valor)).first() if valor.isdigit() else None

def _volver(request, defecto="pedidos:carrito"):
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}
    ):
        return redirect(destino)
    return redirect(defecto)


def ver_carrito(request):
    carrito = Carrito(request)
    contexto = {
        "items": list(carrito),
        "total": carrito.total,
        "problemas": carrito.problemas(),
    }
    return render(request, "pedidos/carrito.html", contexto)


@require_POST
def agregar(request, pk):
    producto = get_object_or_404(
        Producto.objects.prefetch_related("talles", "colores"), pk=pk
    )
    carrito = Carrito(request)
    if carrito.agregar_repartido(producto, _cantidad(request, 0), _colores(request)):
        if request.POST.get("comprar_ahora"):
            return redirect("pedidos:confirmar")
        messages.success(request, f"{producto.nombre} se agregó al carrito.")
    else:
        messages.error(request, carrito.error)
    return _volver(request)


@require_POST
def actualizar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    carrito = Carrito(request)
    if not carrito.actualizar(producto, _cantidad(request, 0), _color(request)):
        messages.error(request, carrito.error)
    return redirect("pedidos:carrito")


@require_POST
def quitar(request, pk):
    color = _color(request)
    Carrito(request).quitar(pk, color.pk if color else None)
    return redirect("pedidos:carrito")


@login_required
def confirmar(request):
    carrito = Carrito(request)
    if len(carrito) == 0:
        messages.error(request, "El carrito está vacío.")
        return redirect("pedidos:carrito")
    
    problemas = carrito.problemas()
    if problemas:
        messages.error(request, " ".join(problemas))
        return redirect("pedidos:carrito")

    if request.method == "POST":
        form = PedidoForm(request.POST)
        if form.is_valid():
            try:
                pedido = crear_pedido(carrito, request.user, form.cleaned_data)
            except (StockInsuficiente) as error:
                messages.error(
                    request,
                    "No hay stock suficiente de: "
                    + ", ".join(error.productos)
                    + ". Ajustá las cantidades.",
                )
                return redirect("pedidos:carrito")
            except CarritoInvalido as error:
                messages.error(request, " ".join(error.problemas))
                return redirect("pedidos:carrito")
            
            return redirect("pedidos:exito", pk=pedido.pk)
    else:
        form = PedidoForm()

    contexto = {"form": form, "items": list(carrito), "total": carrito.total}
    return render(request, "pedidos/confirmar.html", contexto)


@login_required
def exito(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    url = url_whatsapp(settings.NEGOCIO["whatsapp"], mensaje_pedido(pedido))
    return render(
        request, "pedidos/exito.html", {"pedido": pedido, "whatsapp_pedido_url": url}
    )

@login_required
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(cliente=request.user)
    return render(request, "pedidos/mis_pedidos.html", {"pedidos": pedidos})


@login_required
def detalle(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles__producto"),
        pk=pk,
        cliente=request.user,
    )
    return render(request, "pedidos/detalle.html", {"pedido": pedido})

def _cantidad(request, defecto=1):
    """Obtiene la cantidad general (sin color) desde el POST."""
    valor = request.POST.get("cantidad", "")
    return int(valor) if valor.isdigit() else defecto