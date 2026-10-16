from decimal import Decimal

from catalogo.models import Producto

CLAVE_SESION = "carrito"


class Carrito:
    """Carrito guardado en la sesión: {id_producto: cantidad}."""

    def __init__(self, request):
        self.session = request.session
        self.items = self.session.get(CLAVE_SESION, {})

    def _guardar(self):
        self.session[CLAVE_SESION] = self.items
        self.session.modified = True

    def agregar(self, producto, cantidad=1):
        clave = str(producto.pk)
        nueva = self.items.get(clave, 0) + cantidad
        if nueva > producto.stock:
            return False
        self.items[clave] = nueva
        self._guardar()
        return True

    def actualizar(self, producto, cantidad):
        if cantidad <= 0:
            self.quitar(producto.pk)
            return True
        if cantidad > producto.stock:
            return False
        self.items[str(producto.pk)] = cantidad
        self._guardar()
        return True

    def quitar(self, producto_id):
        self.items.pop(str(producto_id), None)
        self._guardar()

    def vaciar(self):
        self.items = {}
        self._guardar()

    def __iter__(self):
        productos = Producto.objects.in_bulk([int(i) for i in self.items])
        for clave, cantidad in self.items.items():
            producto = productos.get(int(clave))
            if producto is None:
                continue
            yield {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": producto.precio * cantidad,
            }

    def __len__(self):
        return sum(self.items.values())

    @property
    def total(self):
        return sum((item["subtotal"] for item in self), Decimal("0"))