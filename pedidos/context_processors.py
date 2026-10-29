from .services import Carrito
from .models import Pedido


def carrito(request):
    return {"carrito_cantidad": len(Carrito(request))}

def pendientes(request):
    usuario = getattr(request, "user", None)
    if request.path != "/admin/" or not (usuario and usuario.is_staff):
        return {}
    cantidad = Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count()
    return {"pedidos_pendientes": cantidad}