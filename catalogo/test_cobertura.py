from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .admin import ProductoAdmin
from .models import Categoria, Marca, Producto


class FiltrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insumos = Categoria.objects.create(nombre="Insumos")
        cls.maquinas = Categoria.objects.create(nombre="Maquinas")
        cls.alfa = Marca.objects.create(nombre="Alfa")
        cls.beta = Marca.objects.create(nombre="Beta")
        Producto.objects.create(
            nombre="Cinta", precio=1500, stock=10,
            categoria=cls.insumos, marca=cls.alfa,
        )
        Producto.objects.create(
            nombre="Taladro", precio=90000, stock=3,
            categoria=cls.maquinas, marca=cls.beta,
        )
        Producto.objects.create(
            nombre="Lijadora", precio=50000, stock=0,
            categoria=cls.maquinas, marca=cls.alfa,
        )

    def test_filtra_por_categoria(self):
        r = self.client.get(
            reverse("catalogo:listado"), {"categoria": self.insumos.pk}
        )
        self.assertContains(r, "Cinta")
        self.assertNotContains(r, "Taladro")
        self.assertNotContains(r, "Lijadora")

    def test_filtra_por_marca(self):
        r = self.client.get(reverse("catalogo:listado"), {"marca": self.beta.pk})
        self.assertContains(r, "Taladro")
        self.assertNotContains(r, "Cinta")
        self.assertNotContains(r, "Lijadora")

    def test_filtros_de_stock_del_panel(self):
        root = User.objects.create_superuser("root", password="Clave-segura-2026")
        self.client.force_login(root)
        esperado = {"sin": "Lijadora", "bajo": "Taladro", "ok": "Cinta"}
        todos = set(esperado.values())
        for filtro, producto in esperado.items():
            with self.subTest(filtro=filtro):
                r = self.client.get(
                    reverse("admin:catalogo_producto_changelist"), {"stock": filtro}
                )
                self.assertContains(r, producto)
                for otro in todos - {producto}:
                    self.assertNotContains(r, otro)

    def test_miniatura_y_vista_previa_del_panel(self):
        modelo = ProductoAdmin(Producto, admin.site)
        con_foto = Producto(nombre="X", imagen="productos/x.jpg")
        self.assertIn("/media/productos/x.jpg", modelo.miniatura(con_foto))
        self.assertIn("/media/productos/x.jpg", modelo.vista_previa(con_foto))
        self.assertEqual(modelo.miniatura(Producto(nombre="Y")), "—")