from .services import Carrito


def carrito(request):
    return {"carrito_cantidad": len(Carrito(request))}