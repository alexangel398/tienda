from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Marca, Producto


class FichaTests(TestCase):
    @classmethod
    def crear(cls, nombre, categoria, stock=3):
        return Producto.objects.create(
            nombre=nombre, precio=100, stock=stock, categoria=categoria, marca=cls.alfa
        )

    @classmethod
    def setUpTestData(cls):
        cls.insumos = Categoria.objects.create(nombre="Insumos")
        cls.sola = Categoria.objects.create(nombre="Sola")
        cls.alfa = Marca.objects.create(nombre="Alfa")
        cls.principal = cls.crear("Cinta", cls.insumos, stock=5)
        for i in range(5):
            cls.crear(f"Insumo {i}", cls.insumos)
        cls.unico = cls.crear("Agotado", cls.sola, stock=0)

    def test_relacionados_son_de_la_misma_categoria_sin_el_producto_actual(self):
        relacionados = list(self.principal.relacionados())
        self.assertEqual(len(relacionados), 4)
        self.assertNotIn(self.principal, relacionados)
        self.assertTrue(all(p.categoria == self.insumos for p in relacionados))

    def test_la_ficha_muestra_cuatro_relacionados(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.principal.pk]))
        self.assertContains(r, "Productos relacionados")
        self.assertContains(r, 'class="agregar-rapido"', count=4)

    def test_sin_relacionados_no_se_muestra_la_seccion(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.unico.pk]))
        self.assertNotContains(r, "Productos relacionados")

    def test_la_ficha_ofrece_cantidad_compra_y_compartir(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.principal.pk]))
        for texto in ["Añadir al carrito", "Comprar ahora", "Compartir", "data-selector"]:
            self.assertContains(r, texto)

    def test_un_producto_sin_stock_no_muestra_el_formulario_de_compra(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.unico.pk]))
        self.assertContains(r, "Sin stock")
        self.assertNotContains(r, "Comprar ahora")

    def test_la_vista_rapida_devuelve_solo_la_ficha(self):
        r = self.client.get(reverse("catalogo:rapida", args=[self.principal.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cinta")
        self.assertContains(r, "Comprar ahora")
        self.assertNotContains(r, "<html")

    def test_la_vista_rapida_de_un_producto_inexistente_da_404(self):
        r = self.client.get(reverse("catalogo:rapida", args=[9999]))
        self.assertEqual(r.status_code, 404)

    def test_las_tarjetas_del_catalogo_tienen_vista_rapida(self):
        r = self.client.get(reverse("catalogo:listado"))
        self.assertContains(r, reverse("catalogo:rapida", args=[self.principal.pk]))