from django.http import HttpResponse
from django.views.decorators.http import require_safe
from django.shortcuts import render

from catalogo.models import Producto


@require_safe
def salud(request):
    # No toca la base de datos: el ping periódico no despierta a Neon.
    return HttpResponse("OK", content_type="text/plain", status=200)

def inicio(request):
    destacados = (
        Producto.objects.filter(stock__gt=0)
        .prefetch_related("talles", "colores")
        .select_related("marca")
        .order_by("-id")[:6]
    )
    return render(request, "paginas/inicio.html", {"destacados": destacados})





def contacto(request):
    return render(request, "paginas/contacto.html")