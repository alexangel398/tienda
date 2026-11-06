from django.conf import settings
from django.db import models


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PREPARADO = "preparado", "Preparado"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    class Entrega(models.TextChoices):
        RETIRO = "retiro", "Retiro en el local"
        ENVIO = "envio", "Envío"

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    entrega = models.CharField(
        max_length=10, choices=Entrega.choices, default=Entrega.RETIRO
    )
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=200, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-fecha"]

    @property
    def badge_class(self):
        return {
            self.Estado.PENDIENTE: "estado-pendiente",
            self.Estado.PREPARADO: "estado-preparado",
            self.Estado.ENTREGADO: "estado-entregado",
            self.Estado.CANCELADO: "estado-cancelado",
        }.get(self.estado, "estado-pendiente")

    def __str__(self):
        return f"Pedido #{self.pk}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.PROTECT, related_name="detalles_pedido"
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=50, blank=True, default="")
    talles = models.CharField(max_length=100, blank=True, default="")    
    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.producto}"