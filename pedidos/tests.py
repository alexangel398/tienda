from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto


class CarritoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        cls.cinta = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )
        cls.taladro = Producto.objects.create(
            nombre="Taladro", precio=Decimal("90000"), stock=0,
            categoria=categoria, marca=marca,
        )

    def agregar(self, producto, cantidad=1):
        return self.client.post(
            reverse("pedidos:agregar", args=[producto.pk]),
            {"cantidad": cantidad},
            follow=True,
        )

    def test_agregar_producto_lo_muestra_en_el_carrito(self):
        r = self.agregar(self.cinta, 2)
        self.assertContains(r, "Cinta")
        self.assertEqual(self.client.session["carrito"], {str(self.cinta.pk): 2})

    def test_las_cantidades_se_suman(self):
        self.agregar(self.cinta, 2)
        self.agregar(self.cinta, 1)
        self.assertEqual(self.client.session["carrito"][str(self.cinta.pk)], 3)

    def test_no_permite_superar_el_stock(self):
        r = self.agregar(self.cinta, 6)
        self.assertContains(r, "No hay stock suficiente")
        self.assertNotIn("carrito", self.client.session)

    def test_producto_sin_stock_no_se_agrega(self):
        r = self.agregar(self.taladro)
        self.assertContains(r, "No hay stock suficiente")
        self.assertNotIn("carrito", self.client.session)

    def test_actualizar_cantidad_y_quitar(self):
        self.agregar(self.cinta, 1)
        self.client.post(
            reverse("pedidos:actualizar", args=[self.cinta.pk]), {"cantidad": 4}
        )
        self.assertEqual(self.client.session["carrito"][str(self.cinta.pk)], 4)
        self.client.post(reverse("pedidos:quitar", args=[self.cinta.pk]))
        self.assertEqual(self.client.session["carrito"], {})

    def test_total_del_carrito(self):
        r = self.agregar(self.cinta, 2)
        self.assertEqual(r.context["total"], Decimal("3000"))

    def test_agregar_vuelve_a_la_pagina_de_origen(self):
        r = self.client.post(
            reverse("pedidos:agregar", args=[self.cinta.pk]),
            {"cantidad": 1, "next": "/catalogo/"},
        )
        self.assertRedirects(r, "/catalogo/")

    def test_agregar_ignora_destinos_externos(self):
        r = self.client.post(
            reverse("pedidos:agregar", args=[self.cinta.pk]),
            {"cantidad": 1, "next": "https://sitio-externo.example/"},
        )
        self.assertRedirects(r, reverse("pedidos:carrito"))

# Create your tests here.
