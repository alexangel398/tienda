import re
from urllib.parse import quote
from django.conf import settings
from decimal import Decimal
from django.db import transaction
from catalogo.models import Producto
from .models import DetallePedido, Pedido
from django.db.models import F

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
    
    
class StockInsuficiente(Exception):
    def __init__(self, productos):
        self.productos = productos
        super().__init__("Stock insuficiente")


def crear_pedido(carrito, cliente, datos):
    items = list(carrito)
    if not items:
        raise ValueError("El carrito está vacío.")

    with transaction.atomic():
        ids = [item["producto"].pk for item in items]
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(pk__in=ids).order_by("pk")
        }

        faltantes = [
            productos[item["producto"].pk].nombre
            for item in items
            if item["cantidad"] > productos[item["producto"].pk].stock
        ]
        if faltantes:
            raise StockInsuficiente(faltantes)

        pedido = Pedido.objects.create(
            cliente=cliente,
            entrega=datos["entrega"],
            telefono=datos["telefono"],
            direccion=datos.get("direccion", ""),
        )
        total = Decimal("0")
        for item in items:
            producto = productos[item["producto"].pk]
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item["cantidad"],
                precio_unitario=producto.precio,
            )
            producto.stock -= item["cantidad"]
            producto.save(update_fields=["stock"])
            total += producto.precio * item["cantidad"]
        pedido.total = total
        pedido.save(update_fields=["total"])

    carrito.vaciar()
    return pedido

TRANSICIONES = {
    Pedido.Estado.PENDIENTE: {Pedido.Estado.PREPARADO, Pedido.Estado.CANCELADO},
    Pedido.Estado.PREPARADO: {Pedido.Estado.ENTREGADO, Pedido.Estado.CANCELADO},
    Pedido.Estado.ENTREGADO: set(),
    Pedido.Estado.CANCELADO: set(),
}


class TransicionInvalida(Exception):
    pass

def reponer_stock(pedido):
    for detalle in pedido.detalles.all():
        Producto.objects.filter(pk=detalle.producto_id).update(
            stock=F("stock") + detalle.cantidad
        )

def cambiar_estado(pedido, nuevo_estado):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if nuevo_estado == pedido.estado:
            return pedido
        if nuevo_estado not in TRANSICIONES[pedido.estado]:
            raise TransicionInvalida(
                f"No se puede pasar de {Pedido.Estado(pedido.estado).label} "
                f"a {Pedido.Estado(nuevo_estado).label}."
            )
        if nuevo_estado == Pedido.Estado.CANCELADO:
            reponer_stock(pedido)
        pedido.estado = nuevo_estado
        pedido.save(update_fields=["estado"])
    return pedido

def telefono_internacional(telefono):
    digitos = re.sub(r"\D", "", telefono).lstrip("0")
    return digitos if digitos.startswith("54") else f"549{digitos}"


def url_whatsapp(numero, mensaje):
    return f"https://wa.me/{numero}?text={quote(mensaje)}"


def mensaje_pedido(pedido):
    lineas = [f"Hola, hice el pedido #{pedido.pk} en {settings.NEGOCIO['nombre']}:", ""]
    for d in pedido.detalles.select_related("producto"):
        lineas.append(f"- {d.cantidad} x {d.producto.nombre} (${d.subtotal:.2f})")
    lineas += [
        "",
        f"Total: ${pedido.total:.2f}",
        f"Entrega: {pedido.get_entrega_display()}",
    ]
    if pedido.direccion:
        lineas.append(f"Dirección: {pedido.direccion}")
    lineas += [f"Teléfono: {pedido.telefono}", f"Cliente: {pedido.cliente.get_username()}"]
    return "\n".join(lineas)