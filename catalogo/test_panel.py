from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from cuentas.services import ROL_COLABORADOR

from .models import Categoria, Marca, Producto


class PanelColaboradorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("crear_roles", verbosity=0)
        colab = User.objects.create_user(
            "colab", password="Clave-segura-2026", is_staff=True
        )
        colab.groups.add(Group.objects.get(name=ROL_COLABORADOR))
        cls.colab = colab
        cls.categoria = Categoria.objects.create(nombre="Insumos")
        cls.marca = Marca.objects.create(nombre="Alfa")

    def setUp(self):
        self.client.force_login(self.colab)

    def datos(self, **cambios):
        base = {
            "nombre": "Cinta",
            "descripcion": "Cinta métrica de 5 metros",
            "categoria": self.categoria.pk,
            "marca": self.marca.pk,
            "precio": "1500",
            "stock": "10",
        }
        return {**base, **cambios}

    def test_colaborador_carga_un_producto(self):
        r = self.client.post(reverse("admin:catalogo_producto_add"), self.datos())
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Producto.objects.filter(nombre="Cinta").exists())

    def test_precio_cero_o_negativo_es_rechazado(self):
        for precio in ["0", "-5"]:
            with self.subTest(precio=precio):
                r = self.client.post(
                    reverse("admin:catalogo_producto_add"), self.datos(precio=precio)
                )
                self.assertEqual(r.status_code, 200)
                self.assertEqual(Producto.objects.count(), 0)

    def test_no_se_borra_una_categoria_con_productos(self):
        Producto.objects.create(
            nombre="Cinta", precio=1500, stock=10,
            categoria=self.categoria, marca=self.marca,
        )
        self.client.post(
            reverse("admin:catalogo_categoria_delete", args=[self.categoria.pk]),
            {"post": "yes"},
        )
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_filtro_de_stock_sin_stock(self):
        Producto.objects.create(
            nombre="Taladro", precio=90000, stock=0,
            categoria=self.categoria, marca=self.marca,
        )
        Producto.objects.create(
            nombre="Cinta", precio=1500, stock=10,
            categoria=self.categoria, marca=self.marca,
        )
        r = self.client.get(
            reverse("admin:catalogo_producto_changelist"), {"stock": "sin"}
        )
        self.assertContains(r, "Taladro")
        self.assertNotContains(r, "Cinta")