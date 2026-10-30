from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Color(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    codigo_hex = models.CharField(max_length=7, help_text="Ej: #000000 para negro")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to="productos/", blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="productos"
    )
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, related_name="productos"
    )
    colores = models.ManyToManyField(Color, blank=True, related_name="productos")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
    
    def relacionados(self, limite=4):
        return (
            Producto.objects.filter(categoria_id=self.categoria_id)
            .exclude(pk=self.pk)
            .select_related("marca", "categoria")[:limite]
        )