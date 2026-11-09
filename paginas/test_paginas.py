import re

from django.test import TestCase, override_settings
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

NEGOCIO = {
    "nombre": "Mi Negocio",
    "ciudad": "CABA",
    "whatsapp": "5491163633835",
    "direccion": "Calle Falsa 123",
    "horarios": "Lunes a viernes de 9 a 18 h",
}


@override_settings(NEGOCIO=NEGOCIO)
class PaginasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        for i in range(8):
            Producto.objects.create(
                nombre=f"Producto {i}", precio=100, stock=3,
                categoria=categoria, marca=marca,
            )
        Producto.objects.create(
            nombre="Agotado", precio=100, stock=0, categoria=categoria, marca=marca
        )
        cls.paginas = [reverse("paginas:inicio"), reverse("paginas:contacto")]

    def test_el_inicio_es_la_raiz_del_sitio(self):
        self.assertEqual(reverse("paginas:inicio"), "/")

    def test_las_paginas_cargan(self):
        for url in self.paginas:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_la_pagina_de_historia_ya_no_existe(self):
        self.assertEqual(self.client.get("/historia/").status_code, 404)

    def test_el_inicio_muestra_hasta_seis_productos_con_stock(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertEqual(len(r.context["destacados"]), 6)
        self.assertNotContains(r, "Agotado")

    def test_contacto_muestra_direccion_horarios_y_mapa(self):
        r = self.client.get(reverse("paginas:contacto"))
        self.assertContains(r, "Calle Falsa 123")
        self.assertContains(r, "Lunes a viernes de 9 a 18 h")
        self.assertContains(r, "Calle%20Falsa%20123")

    def test_cada_pagina_tiene_titulo_y_descripcion(self):
        for url in self.paginas + [reverse("catalogo:listado")]:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                titulo = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
                descripcion = re.search(
                    r'<meta name="description" content="([^"]*)"', html
                )
                self.assertIsNotNone(titulo)
                self.assertTrue(titulo.group(1).strip())
                self.assertIsNotNone(descripcion)
                self.assertTrue(descripcion.group(1).strip())

    def test_el_titulo_del_inicio_nombra_a_la_marca(self):
        html = self.client.get(reverse("paginas:inicio")).content.decode()
        self.assertRegex(html, r"<title>[^<]*Zairux[^<]*</title>")

    def test_la_cabecera_tiene_marca_menu_y_buscador(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, '<span class="acento">Negocio</span>')
        self.assertContains(r, 'role="search"')
        for texto in ["Catálogo", "Contacto"]:
            self.assertContains(r, texto)
        self.assertNotContains(r, "Nuestra historia")

    def test_el_contador_del_carrito_aparece_con_productos(self):
        producto = Producto.objects.filter(stock__gt=0).first()
        self.client.post(
            reverse("pedidos:agregar", args=[producto.pk]), {"cantidad": 2}
        )
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, '<span class="contador">2</span>')

    def test_el_inicio_permite_agregar_productos_al_carrito(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, "Añadir al carrito")


@override_settings(
    NEGOCIO={
        **NEGOCIO,
        "rubro": "Indumentaria de prueba",
        "lema": "Lema De Prueba",
        "facebook": "https://facebook.com/x",
        "tiktok": "https://tiktok.com/@x",
    }
)
class IdentidadTests(TestCase):
    def test_el_pie_muestra_solo_las_redes_configuradas(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, "https://facebook.com/x")
        self.assertContains(r, "https://tiktok.com/@x")
        self.assertNotContains(r, "Instagram")

    def test_el_rubro_y_el_lema_salen_de_la_configuracion(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, "Indumentaria de prueba")  # <--- Cambiá "Ropa en CABA" por esto
        self.assertContains(r, "lema de prueba")
        self.assertNotContains(r, "Insumos y máquinas")

    def test_la_portada_muestra_el_logo(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, "portada-logo")