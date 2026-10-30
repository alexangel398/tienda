from django.contrib import admin
from django.utils.html import format_html

from .models import Categoria, Marca, Color, Producto

STOCK_BAJO = 5

admin.site.site_header = "Panel de la tienda"
admin.site.site_title = "Panel de la tienda"
admin.site.index_title = "Gestión del catálogo y los pedidos"


class StockFilter(admin.SimpleListFilter):
    title = "stock"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return [
            ("sin", "Sin stock"),
            ("bajo", f"Stock bajo ({STOCK_BAJO} o menos)"),
            ("ok", "Con stock"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "sin":
            return queryset.filter(stock=0)
        if self.value() == "bajo":
            return queryset.filter(stock__gt=0, stock__lte=STOCK_BAJO)
        if self.value() == "ok":
            return queryset.filter(stock__gt=STOCK_BAJO)
        return queryset


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["miniatura", "nombre", "marca", "categoria", "precio", "stock"]
    list_display_links = ["nombre"]
    list_editable = ["precio", "stock"]
    list_filter = ["categoria", "marca", StockFilter, "colores"]
    search_fields = ["nombre", "marca__nombre"]
    autocomplete_fields = ["categoria", "marca", "colores"]
    raw_id_fields = ["colores"]
    list_per_page = 25
    readonly_fields = ["vista_previa"]
    fieldsets = [
        ("Datos del producto", {"fields": ["nombre", "descripcion", "categoria", "marca", "colores"]}),
        ("Precio y stock", {"fields": ["precio", "stock"]}),
        ("Imagen", {"fields": ["imagen", "vista_previa"]}),
    ]

    @admin.display(description="Foto")
    def miniatura(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;">', obj.imagen.url
            )
        return "—"

    @admin.display(description="Vista previa")
    def vista_previa(self, obj):
        if obj and obj.imagen:
            return format_html(
                '<img src="{}" style="height:120px;border-radius:4px;">', obj.imagen.url
            )
        return "—"