import re
from collections import defaultdict
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.db.models import F

from catalogo.models import Color, Producto

from .models import DetallePedido, Pedido

CLAVE_SESION = "carrito"
COLOR_A_COORDINAR = "Color a coordinar"


def aviso_de_curva(producto, total):
    """Aviso si el total de un modelo no llega a una curva completa."""
    minimo = producto.minimo_compra
    if total >= minimo:
        return ""
    return (
        f"{producto.nombre} se vende desde {minimo} unidades en total "
        f"(una curva completa): te faltan {minimo - total}."
    )

def repartir(total, colores):
    """Reparte `total` unidades en partes iguales entre los colores elegidos.
    El resto va a los primeros. Sin colores, todo queda sin color (clave None)."""
    if not colores:
        return {None: total}
    base, resto = divmod(total, len(colores))
    return {color: base + (1 if i < resto else 0) for i, color in enumerate(colores)}
class Carrito:
    """Carrito guardado en la sesión: {clave: cantidad}.

    La clave es el id del producto, o "producto:color" si se eligió un color.
    Un modelo puede repartirse en varios colores (y en "sin color", a coordinar
    con el vendedor). La curva, una unidad por talle, se exige sobre el TOTAL del
    modelo, y el stock también es uno solo por modelo.
    """

    def __init__(self, request):
        self.session = request.session
        self.items = self.session.get(CLAVE_SESION, {})
        self.error = ""

    @staticmethod
    def _clave(producto_id, color_id=None):
        return f"{producto_id}:{color_id}" if color_id else str(producto_id)

    @staticmethod
    def _separar(clave):
        producto_id, _, color_id = clave.partition(":")
        return int(producto_id), (int(color_id) if color_id else None)

    def _unidades_de(self, producto_id, excepto=None):
        return sum(
            cantidad
            for clave, cantidad in self.items.items()
            if clave != excepto and self._separar(clave)[0] == producto_id
        )
        
    def _guardar(self):
        self.session[CLAVE_SESION] = self.items
        self.session.modified = True

    def _rechazar(self, motivo):
        self.error = motivo
        return False

    def agregar_varios(self, producto, cantidades):
        """cantidades: {color o None: unidades}. Se valida el modelo completo."""
        cantidades = {color: n for color, n in cantidades.items() if n > 0}
        if not cantidades:
            return self._rechazar("Elegí cuántas unidades querés.")
        disponibles = list(producto.colores.all())
        for color in cantidades:
            if color is not None and color not in disponibles:
                return self._rechazar(f"{producto.nombre} no está disponible en ese color.")
        total = self._unidades_de(producto.pk) + sum(cantidades.values())
        motivo = aviso_de_curva(producto, total)
        if motivo:
            return self._rechazar(motivo)
        if total > producto.stock:
            return self._rechazar(f"No hay stock suficiente de {producto.nombre}.")
        for color, n in cantidades.items():
            clave = self._clave(producto.pk, color.pk if color else None)
            self.items[clave] = self.items.get(clave, 0) + n
        self._guardar()
        return True
    
    def agregar_repartido(self, producto, total, colores):
        """Agrega `total` unidades repartidas entre los colores tildados en la ficha."""
        if total <= 0:
            return self._rechazar("Elegí cuántas unidades querés.")
        if len(colores) > total:
            return self._rechazar(
                f"Elegiste {len(colores)} colores y {total} unidades: "
                "subí la cantidad o sacá algún color."
            )
        return self.agregar_varios(producto, repartir(total, colores))

    def agregar(self, producto, cantidad=1, color=None):
        return self.agregar_varios(producto, {color: cantidad})

    def actualizar(self, producto, cantidad, color=None):
        color_id = color.pk if color else None
        if cantidad <= 0:
            self.quitar(producto.pk, color_id)
            return True
        clave = self._clave(producto.pk, color_id)
        if cantidad + self._unidades_de(producto.pk, excepto=clave) > producto.stock:
            return self._rechazar(f"No hay stock suficiente de {producto.nombre}.")
        self.items[clave] = cantidad
        self._guardar()
        return True

    def quitar(self, producto_id, color_id=None):
        self.items.pop(self._clave(producto_id, color_id), None)
        self._guardar()

    def vaciar(self):
        self.items = {}
        self._guardar()

    def problemas(self):
        """Avisos de los modelos del carrito que no llegan a una curva completa."""
        totales = defaultdict(int)
        for clave, cantidad in self.items.items():
            totales[self._separar(clave)[0]] += cantidad
        productos = Producto.objects.prefetch_related("talles").in_bulk(totales)
        avisos = (
            aviso_de_curva(productos[pk], total)
            for pk, total in totales.items()
            if pk in productos
        )
        return [aviso for aviso in avisos if aviso]

    def __iter__(self):
        pares = [self._separar(clave) for clave in self.items]
        productos = Producto.objects.prefetch_related("talles", "colores").in_bulk(
            {producto_id for producto_id, _ in pares}
        )
        colores = Color.objects.in_bulk({color_id for _, color_id in pares if color_id})
        for clave, cantidad in self.items.items():
            producto_id, color_id = self._separar(clave)
            producto = productos.get(producto_id)
            if producto is None:
                continue
            otras = self._unidades_de(producto_id, excepto=clave)
            yield {
                "producto": producto,
                "color": colores.get(color_id),
                "color_id": color_id,
                "cantidad": cantidad,
                "minimo": producto.minimo_compra,
                "maximo": max(producto.stock - otras, 0),
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


class CarritoInvalido(Exception):
    def __init__(self, problemas):
        self.problemas = problemas
        super().__init__("; ".join(problemas))


def crear_pedido(carrito, cliente, datos):
    items = list(carrito)
    if not items:
        raise ValueError("El carrito está vacío.")

    with transaction.atomic():
        ids = [item["producto"].pk for item in items]
        productos = {
            p.pk: p
            for p in Producto.objects.select_for_update()
            .prefetch_related("talles", "colores")
            .filter(pk__in=ids)
            .order_by("pk")
        }

        # Se revisa todo de nuevo con los datos bloqueados: los talles, los colores
        # y el stock pudieron cambiar desde que se armó el carrito.
        pedidas = defaultdict(int)
        problemas = []
        for item in items:
            producto = productos[item["producto"].pk]
            pedidas[producto.pk] += item["cantidad"]
            if item["color"] is not None and item["color"] not in producto.colores.all():
                problemas.append(f"{producto.nombre} no está disponible en ese color.")
        for pk, total in pedidas.items():
            aviso = aviso_de_curva(productos[pk], total)
            if aviso:
                problemas.append(aviso)

        faltantes = [
            productos[pk].nombre
            for pk, cantidad in pedidas.items()
            if cantidad > productos[pk].stock
        ]
        if faltantes:
            raise StockInsuficiente(faltantes)
        if problemas:
            raise CarritoInvalido(problemas)

        pedido = Pedido.objects.create(
            cliente=cliente,
            entrega=datos["entrega"],
            telefono=datos["telefono"],
            direccion=datos.get("direccion", ""),
        )
        total = Decimal("0")
        for item in items:
            producto = productos[item["producto"].pk]
            if item["color"]:
                color = item["color"].nombre
            else:
                color = COLOR_A_COORDINAR if producto.colores.all() else ""
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item["cantidad"],
                precio_unitario=producto.precio,
                color=color,
                talles=", ".join(t.nombre for t in producto.talles.all()),
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
        partes = [f"{d.cantidad} x {d.producto.nombre}"]
        if d.color:
            partes.append(d.color)
        if d.talles:
            partes.append(f"talles {d.talles}")
        lineas.append(f"- {' · '.join(partes)} (${d.subtotal:.2f})")
    lineas += ["", f"Total: ${pedido.total:.2f}", f"Entrega: {pedido.get_entrega_display()}"]
    if pedido.entrega == Pedido.Entrega.ENVIO:
        lineas.append("Dirección: a coordinar por este chat")
    lineas += [f"Teléfono: {pedido.telefono}", f"Cliente: {pedido.cliente.get_username()}"]
    return "\n".join(lineas)