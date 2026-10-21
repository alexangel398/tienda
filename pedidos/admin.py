from django.contrib import admin, messages

from .models import DetallePedido, Pedido
from .services import TransicionInvalida, cambiar_estado


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    can_delete = False
    readonly_fields = ["producto", "cantidad", "precio_unitario"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "cliente", "fecha", "estado", "entrega", "total"]
    list_filter = ["estado", "entrega"]
    search_fields = ["cliente__username", "telefono"]
    readonly_fields = ["cliente", "fecha", "total"]
    inlines = [DetallePedidoInline]
    actions = ["cancelar"]

    def has_add_permission(self, request):
        return False

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

    @admin.action(
        description="Cancelar pedidos seleccionados (repone el stock)",
        permissions=["change"],
    )
    def cancelar(self, request, queryset):
        cancelados = 0
        for pedido in queryset:
            try:
                cambiar_estado(pedido, Pedido.Estado.CANCELADO)
                cancelados += 1
            except TransicionInvalida as error:
                self.message_user(
                    request, f"Pedido #{pedido.pk}: {error}", messages.WARNING
                )
        if cancelados:
            self.message_user(
                request, f"{cancelados} pedido(s) cancelado(s).", messages.SUCCESS
            )