from django.contrib import admin

from .models import Categoria, Marca, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "marca", "categoria", "precio", "stock"]
    list_filter = ["categoria", "marca"]
    search_fields = ["nombre"]