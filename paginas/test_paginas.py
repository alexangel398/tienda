import re

from django.test import TestCase, override_settings
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

NEGOCIO = {
    "nombre": "Mi Negocio",
    "ciudad": "Rosario",
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
        cls.paginas = [
            reverse("paginas:inicio"),
            reverse("paginas:historia"),
            reverse("paginas:contacto"),
        ]

    def test_el_inicio_es_la_raiz_del_sitio(self):
        self.assertEqual(reverse("paginas:inicio"), "/")

    def test_las_tres_paginas_cargan(self):
        for url in self.paginas:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_el_inicio_muestra_hasta_seis_productos_con_stock(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertEqual(len(r.context["destacados"]), 6)
        self.assertNotContains(r, "Agotado")

    def test_contacto_muestra_direccion_horarios_y_mapa(self):
        r = self.client.get(reverse("paginas:contacto"))
        self.assertContains(r, "Calle Falsa 123")
        self.assertContains(r, "Lunes a viernes de 9 a 18 h")
        self.assertContains(r, "Calle%20Falsa%20123")

    def test_cada_pagina_tiene_titulo_y_descripcion_propios(self):
        descripciones = set()
        for url in self.paginas:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertRegex(
                    html, r"<title>[^<]*Mi Negocio[^<]*Rosario[^<]*</title>"
                )
# Regex flexible para capturar el content de la description sin importar comillas
                descripcion = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
                self.assertIsNotNone(descripcion, f"No se encontró la meta description en {url}")
                descripciones.add(descripcion.group(1))
        self.assertEqual(len(descripciones), 3)
        
    def test_la_cabecera_tiene_marca_menu_y_buscador(self):
        r = self.client.get(reverse("paginas:inicio"))
        self.assertContains(r, '<span class="acento">Negocio</span>')
        self.assertContains(r, 'role="search"')
        for texto in ["Catálogo", "Nuestra historia", "Contacto"]:
            self.assertContains(r, texto)

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