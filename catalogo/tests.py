from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Marca, Producto


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Insumos")
        alfa = Marca.objects.create(nombre="Alfa")
        beta = Marca.objects.create(nombre="Beta")
        Producto.objects.create(
            nombre="Cinta métrica", precio=1500, stock=5, categoria=categoria, marca=alfa
        )
        Producto.objects.create(
            nombre="Taladro", precio=90000, stock=0, categoria=categoria, marca=beta
        )
        cls.url = reverse("catalogo:listado")

    def test_listado_muestra_todos_los_productos(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cinta métrica")
        self.assertContains(r, "Taladro")

    def test_busqueda_por_nombre(self):
        r = self.client.get(self.url, {"q": "taladro"})
        self.assertContains(r, "Taladro")
        self.assertNotContains(r, "Cinta métrica")

    def test_busqueda_por_marca_devuelve_sus_productos(self):
        r = self.client.get(self.url, {"q": "alfa"})
        self.assertContains(r, "Cinta métrica")
        self.assertNotContains(r, "Taladro")

    def test_busqueda_sin_resultados(self):
        r = self.client.get(self.url, {"q": "zzz"})
        self.assertContains(r, "No hay productos con esos filtros")

    def test_filtro_invalido_no_rompe(self):
        r = self.client.get(self.url, {"categoria": "abc"})
        self.assertEqual(r.status_code, 200)

    def test_detalle_inexistente_da_404(self):
        r = self.client.get(reverse("catalogo:detalle", args=[9999]))
        self.assertEqual(r.status_code, 404)