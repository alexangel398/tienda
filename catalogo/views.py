from django.shortcuts import get_object_or_404, render

from .models import Categoria, Marca, Producto
from django.db.models import Q

def _a_entero(valor):
    return int(valor) if valor and valor.isdigit() else None

def listado(request):
    categoria_id = _a_entero(request.GET.get("categoria"))
    marca_id = _a_entero(request.GET.get("marca"))
    q = request.GET.get("q", "").strip()

    productos = Producto.objects.select_related("categoria", "marca")
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if marca_id:
        productos = productos.filter(marca_id=marca_id)
    if q:
        productos = productos.filter(
            Q(nombre__icontains=q) | Q(marca__nombre__icontains=q)
        )

    contexto = {
        "productos": productos,
        "categorias": Categoria.objects.all(),
        "marcas": Marca.objects.all(),
        "categoria_id": categoria_id,
        "marca_id": marca_id,
        "q": q,
    }
    return render(request, "catalogo/listado.html", contexto)


def detalle(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria", "marca").prefetch_related("imagenes", "talles", "colores"), pk=pk
    )
    contexto = {"producto": producto, "relacionados": producto.relacionados()}
    return render(request, "catalogo/detalle.html", contexto)


def rapida(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria", "marca").prefetch_related("imagenes", "talles", "colores"), pk=pk
    )
    return render(request, "partes/producto_ficha.html", {"p": producto, "rapida": True})