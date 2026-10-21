from django.contrib import admin

from .models import DetallePedido, Pedido


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

    def has_add_permission(self, request):
        return False