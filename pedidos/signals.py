from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Pedido
from .services import reponer_stock

ESTADOS_CON_STOCK_DESCONTADO = {Pedido.Estado.PENDIENTE, Pedido.Estado.PREPARADO}


@receiver(pre_delete, sender=Pedido)
def reponer_stock_al_borrar(sender, instance, **kwargs):
    # Se lee el estado de la base y no del objeto en memoria, que podría estar desactualizado.
    estado = (
        Pedido.objects.filter(pk=instance.pk).values_list("estado", flat=True).first()
    )
    if estado in ESTADOS_CON_STOCK_DESCONTADO:
        reponer_stock(instance)