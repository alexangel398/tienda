from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import DetallePedido, Pedido
from .services import (
    TransicionInvalida,
    cambiar_estado,
    telefono_internacional,
    url_whatsapp,
)

DIAS_DEMORA = 2
Estado = Pedido.Estado


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    can_delete = False
    readonly_fields = ["producto", "color", "talles", "cantidad", "precio_unitario"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        "id", "cliente", "fecha", "antiguedad", "estado", "entrega", "total", "contacto",
    ]
    list_filter = ["estado", "entrega"]
    search_fields = ["cliente__username", "telefono"]
    readonly_fields = ["cliente", "fecha", "total", "contacto"]
    inlines = [DetallePedidoInline]
    actions = ["marcar_preparado", "marcar_entregado", "cancelar"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Antigüedad", ordering="fecha")
    def antiguedad(self, obj):
        texto = timesince(obj.fecha)
        limite = timezone.now() - timedelta(days=DIAS_DEMORA)
        if obj.estado == Estado.PENDIENTE and obj.fecha < limite:
            return format_html(
                '<strong style="color:#b91c1c">{} · sin atender</strong>', texto
            )
        return texto

    @admin.display(description="Contactar al cliente")
    def contacto(self, obj):
        if not obj.pk:
            return "—"
        mensaje = f"Hola, te escribo por tu pedido #{obj.pk} en {settings.NEGOCIO['nombre']}."
        url = url_whatsapp(telefono_internacional(obj.telefono), mensaje)
        return format_html('<a href="{}" target="_blank" rel="noopener">WhatsApp</a>', url)

    def save_model(self, request, obj, form, change):
        cambia_estado = change and "estado" in form.changed_data
        nuevo = obj.estado
        if cambia_estado:
            obj.estado = form.initial["estado"]
        super().save_model(request, obj, form, change)
        if cambia_estado:
            try:
                obj.estado = cambiar_estado(obj, nuevo).estado
            except TransicionInvalida as error:
                self.message_user(request, str(error), messages.ERROR)

    def _cambiar_varios(self, request, queryset, estado, etiqueta):
        hechos = 0
        for pedido in queryset:
            try:
                cambiar_estado(pedido, estado)
                hechos += 1
            except TransicionInvalida as error:
                self.message_user(
                    request, f"Pedido #{pedido.pk}: {error}", messages.WARNING
                )
        if hechos:
            self.message_user(
                request, f"{hechos} pedido(s) {etiqueta}.", messages.SUCCESS
            )

    @admin.action(description="Marcar como preparados", permissions=["change"])
    def marcar_preparado(self, request, queryset):
        self._cambiar_varios(
            request, queryset, Estado.PREPARADO, "marcado(s) como preparado(s)"
        )

    @admin.action(description="Marcar como entregados", permissions=["change"])
    def marcar_entregado(self, request, queryset):
        self._cambiar_varios(
            request, queryset, Estado.ENTREGADO, "marcado(s) como entregado(s)"
        )

    @admin.action(
        description="Cancelar pedidos seleccionados (repone el stock)",
        permissions=["change"],
    )
    def cancelar(self, request, queryset):
        self._cambiar_varios(request, queryset, Estado.CANCELADO, "cancelado(s)")