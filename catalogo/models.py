from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from .imagenes import optimizar_campo


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
        verbose_name_plural = "colores"

    def __str__(self):
        return self.nombre

class Talle(models.Model):
    nombre = models.CharField(
        max_length=20, unique=True, help_text="Ej: S, M, L, 42 o Talle único"
    )
    orden = models.PositiveSmallIntegerField(
        default=0, help_text="Para mostrar los talles de menor a mayor"
    )

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

class ImagenOptimizadaMixin(models.Model):
    """Optimiza el campo `imagen` cuando se sube una foto nueva."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.imagen = optimizar_campo(self.imagen)
        super().save(*args, **kwargs)

class Producto(ImagenOptimizadaMixin, models.Model):
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
    talles = models.ManyToManyField(Talle, blank=True, related_name="productos")
    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
    
    def relacionados(self, limite=4):
        return (
            Producto.objects.filter(categoria_id=self.categoria_id)
            .exclude(pk=self.pk)
            .select_related("marca", "categoria")[:limite]
            .prefetch_related("talles")
        )
        
    @property
    def fotos(self):
        """La foto principal seguida de las adicionales, para el visor."""
        lista = [self.imagen] if self.imagen else []
        lista += [adicional.imagen for adicional in self.imagenes.all()]
        return lista
    
    @property
    def minimo_compra(self):
        """Una curva: una unidad de cada talle. Sin talles, se vende de a una."""
        return max(len(self.talles.all()), 1)

    @property
    def precio_curva(self):
        return self.precio * self.minimo_compra

class ImagenProducto(ImagenOptimizadaMixin, models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="imagenes"
    )
    imagen = models.ImageField(upload_to="productos/")
    descripcion = models.CharField(
        max_length=100, blank=True, help_text="Ej: Frente, Espalda o Detalle de la tela"
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "imagen adicional"
        verbose_name_plural = "imágenes adicionales"

    def __str__(self):
        return self.descripcion or f"Imagen de {self.producto}"