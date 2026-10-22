from django.test import TestCase, override_settings
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

NEGOCIO = {
    "nombre": "Mi Negocio",
    "whatsapp": "5491163633835",
    "direccion": "Calle Falsa 123",
    "horarios": "Lunes a viernes",
}


@override_settings(NEGOCIO=NEGOCIO)
class WhatsAppTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        cls.producto = Producto.objects.create(
            nombre="Cinta métrica", precio=1500, stock=0,
            categoria=categoria, marca=marca,
        )

    def test_el_boton_aparece_en_todas_las_paginas(self):
        urls = [
            reverse("catalogo:listado"),
            reverse("pedidos:carrito"),
            reverse("cuentas:login"),
            reverse("catalogo:detalle", args=[self.producto.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertContains(r, "https://wa.me/5491163633835?text=")

    def test_consultar_por_producto_lleva_el_nombre_en_el_mensaje(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertContains(r, "Consultar por este producto")
        self.assertContains(r, "Cinta%20m%C3%A9trica")

    def test_el_nombre_del_negocio_sale_de_la_configuracion(self):
        r = self.client.get(reverse("catalogo:listado"))
        self.assertContains(r, "Mi Negocio")