from django.contrib.auth.models import User
from django.urls import reverse

from .ayudas_tests import ArchivosTemporalesTestCase, foto
from .models import Categoria, Color, ImagenProducto, Marca, Producto, Talle


class TextilTests(ArchivosTemporalesTestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Ropa")
        marca = Marca.objects.create(nombre="Lacoste")
        cls.remera = Producto.objects.create(
            nombre="Remera", precio=5000, stock=4, categoria=categoria, marca=marca
        )
        cls.url = reverse("catalogo:detalle", args=[cls.remera.pk])

    def test_la_migracion_carga_los_talles_y_colores_base(self):
        self.assertTrue(Talle.objects.filter(nombre="Talle único").exists())
        self.assertTrue(Talle.objects.filter(nombre="XL").exists())
        self.assertTrue(Color.objects.filter(nombre="Negro", codigo_hex="#000000").exists())

    def test_los_talles_salen_de_menor_a_mayor(self):
        nombres = list(
            Talle.objects.filter(nombre__in=["XL", "S", "L", "M"]).values_list(
                "nombre", flat=True
            )
        )
        self.assertEqual(nombres, ["S", "M", "L", "XL"])

    def test_un_producto_sin_talles_ni_fotos_adicionales_es_valido(self):
        self.assertEqual(self.remera.talles.count(), 0)
        self.assertEqual(self.remera.imagenes.count(), 0)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Talles disponibles")

    def test_la_ficha_muestra_talles_y_colores_disponibles(self):
# Asignamos una imagen para que el visor y la plantilla rendericen completo
        self.remera.imagen = foto()
        self.remera.save()
        
        self.remera.talles.set(Talle.objects.filter(nombre__in=["M", "L"]))
        self.remera.colores.set(Color.objects.filter(nombre="Negro"))
        r = self.client.get(self.url)
        self.assertContains(r, "Talles disponibles")
        self.assertContains(r, ">M</li>")
        self.assertContains(r, ">L</li>")
        self.assertContains(r, 'name="colores"')
        self.assertContains(r, "#000000")

    def test_las_fotos_adicionales_se_optimizan_y_aparecen_en_la_galeria(self):
        extra = ImagenProducto.objects.create(
            producto=self.remera, imagen=foto("espalda.jpg"), descripcion="Espalda"
        )
        self.assertTrue(extra.imagen.name.endswith(".webp"))
        r = self.client.get(self.url)
        self.assertContains(r, "data-pista")
        self.assertContains(r, extra.imagen.url)

    def test_las_imagenes_se_ordenan_por_el_campo_orden(self):
        segunda = ImagenProducto.objects.create(
            producto=self.remera, imagen=foto("b.jpg"), orden=2
        )
        primera = ImagenProducto.objects.create(
            producto=self.remera, imagen=foto("a.jpg"), orden=1
        )
        self.assertEqual(list(self.remera.imagenes.all()), [primera, segunda])

    def test_borrar_el_producto_borra_sus_fotos_adicionales(self):
        ImagenProducto.objects.create(producto=self.remera, imagen=foto("a.jpg"))
        self.remera.delete()
        self.assertEqual(ImagenProducto.objects.count(), 0)

    def test_el_panel_ofrece_talles_colores_y_galeria(self):
        self.client.force_login(
            User.objects.create_superuser("root", password="Clave-segura-2026")
        )
        r = self.client.get(reverse("admin:catalogo_producto_add"))
        for texto in [
            "Talles y colores disponibles",
            'name="talles"',
            'name="colores"',
            "imagenes-TOTAL_FORMS",
        ]:
            self.assertContains(r, texto)
    def test_con_varias_fotos_hay_visor_con_flechas_y_puntos(self):
        ImagenProducto.objects.create(producto=self.remera, imagen=foto("a.jpg"))
        ImagenProducto.objects.create(producto=self.remera, imagen=foto("b.jpg"))
        r = self.client.get(self.url)
        self.assertContains(r, "data-pista")
        self.assertContains(r, "data-siguiente")
        self.assertContains(r, "data-punto", count=2)

    def test_con_una_sola_foto_no_hay_flechas_ni_puntos(self):
        ImagenProducto.objects.create(producto=self.remera, imagen=foto("a.jpg"))
        r = self.client.get(self.url)
        self.assertNotContains(r, "data-siguiente")
        self.assertNotContains(r, "data-punto")

    def test_fotos_devuelve_la_principal_y_luego_las_adicionales(self):
        producto = Producto.objects.create(
            nombre="Short", precio=1, stock=1, imagen=foto("principal.jpg"),
            categoria=self.remera.categoria, marca=self.remera.marca,
        )
        ImagenProducto.objects.create(producto=producto, imagen=foto("espalda.jpg"))
        nombres = [f.name for f in producto.fotos]
        self.assertTrue(nombres[0].startswith("productos/principal"))
        self.assertTrue(nombres[1].startswith("productos/espalda"))
        
    def asignar(self, *nombres):
        self.remera.talles.set(Talle.objects.filter(nombre__in=nombres))

    def test_los_talles_numericos_se_cargan_y_salen_en_orden(self):
        nombres = list(
            Talle.objects.filter(nombre__in=["10", "2", "1"]).values_list("nombre", flat=True)
        )
        self.assertEqual(nombres, ["1", "2", "10"])

    def test_el_minimo_de_compra_es_la_cantidad_de_talles(self):
        self.assertEqual(self.remera.minimo_compra, 1)
        self.asignar("2", "3", "4", "5")
        self.assertEqual(self.remera.minimo_compra, 4)
        self.asignar("1", "2", "3", "4", "5")
        self.assertEqual(self.remera.minimo_compra, 5)

    def test_el_precio_de_la_curva_es_el_precio_por_el_minimo(self):
        self.asignar("1", "2", "3", "4", "5")
        self.assertEqual(self.remera.precio_curva, 25000)

    def test_la_ficha_muestra_la_curva_y_el_selector_arranca_en_el_minimo(self):
        self.asignar("2", "3", "4", "5")
        r = self.client.get(self.url)
        self.assertContains(r, "Curva de 4 unidades")
        self.assertContains(r, 'value="4" min="4"')

    def test_la_tarjeta_agrega_la_curva_completa(self):
        self.asignar("2", "3", "4", "5")
        r = self.client.get(reverse("catalogo:listado"))
        self.assertContains(r, 'name="cantidad" value="4"')

    def test_si_el_stock_no_alcanza_para_una_curva_no_se_puede_comprar(self):
        self.asignar("1", "2", "3", "4", "5")  # curva de 5, stock de 4
        r = self.client.get(self.url)
        self.assertContains(r, "no alcanza")
        self.assertNotContains(r, "Comprar ahora")