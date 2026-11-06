from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Color, Marca, Producto, Talle

from .models import Pedido
from .services import mensaje_pedido

CLAVE = "Clave-segura-2026"
DATOS = {"entrega": "retiro", "telefono": "1155551234"}


class CurvaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Ropa")
        marca = Marca.objects.create(nombre="Zairux")
        cls.negro = Color.objects.get(nombre="Negro")
        cls.blanco = Color.objects.get(nombre="Blanco")
        cls.rojo = Color.objects.get(nombre="Rojo")

        cls.remera = Producto.objects.create(
            nombre="Remera", precio=Decimal("1000"), stock=20,
            categoria=categoria, marca=marca,
        )
        cls.remera.talles.set(Talle.objects.filter(nombre__in=["2", "3", "4", "5"]))
        cls.remera.colores.set([cls.negro, cls.blanco])

        cls.short = Producto.objects.create(
            nombre="Short", precio=Decimal("800"), stock=20,
            categoria=categoria, marca=marca,
        )
        cls.short.talles.set(Talle.objects.filter(nombre__in=["1", "2", "3"]))

        cls.usuario = User.objects.create_user("ana", password=CLAVE)

    def agregar(self, producto, cantidad, color=None):
        datos = {"cantidad": cantidad}
        if color:
            datos["color"] = color.pk
        return self.client.post(
            reverse("pedidos:agregar", args=[producto.pk]), datos, follow=True
        )

    def clave(self, producto, color=None):
        return f"{producto.pk}:{color.pk}" if color else str(producto.pk)

    def carrito(self):
        return self.client.session.get("carrito", {})

    def pedir(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 5, self.blanco)
        return self.client.post(reverse("pedidos:confirmar"), DATOS)

    # --- carrito ---
    def test_no_se_puede_agregar_menos_que_una_curva(self):
        r = self.agregar(self.remera, 2, self.negro)
        self.assertContains(r, "se vende desde 4 unidades por color")
        self.assertEqual(self.carrito(), {})

    def test_la_curva_completa_se_agrega_y_despues_se_suman_unidades_sueltas(self):
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 2, self.negro)
        self.assertEqual(self.carrito(), {self.clave(self.remera, self.negro): 6})

    def test_cada_color_necesita_su_propia_curva(self):
        self.agregar(self.remera, 4, self.negro)
        r = self.agregar(self.remera, 2, self.blanco)
        self.assertContains(r, "se vende desde 4 unidades por color")
        self.agregar(self.remera, 4, self.blanco)
        self.assertEqual(
            self.carrito(),
            {
                self.clave(self.remera, self.negro): 4,
                self.clave(self.remera, self.blanco): 4,
            },
        )

    def test_otro_modelo_no_completa_el_minimo(self):
        self.agregar(self.remera, 4, self.negro)
        r = self.agregar(self.short, 2)
        self.assertContains(r, "se vende desde 3 unidades")
        self.assertEqual(self.carrito(), {self.clave(self.remera, self.negro): 4})

    def test_hay_que_elegir_color_si_el_modelo_tiene_colores(self):
        r = self.agregar(self.remera, 4)
        self.assertContains(r, "Elegí un color")
        self.assertEqual(self.carrito(), {})

    def test_un_color_que_no_es_del_modelo_se_rechaza(self):
        r = self.agregar(self.remera, 4, self.rojo)
        self.assertContains(r, "no está disponible en ese color")

    def test_el_stock_se_comparte_entre_los_colores(self):
        Producto.objects.filter(pk=self.remera.pk).update(stock=6)
        self.agregar(self.remera, 4, self.negro)
        r = self.agregar(self.remera, 4, self.blanco)
        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(len(self.carrito()), 1)

    def test_actualizar_no_permite_bajar_de_la_curva(self):
        self.agregar(self.remera, 6, self.negro)
        url = reverse("pedidos:actualizar", args=[self.remera.pk])
        r = self.client.post(url, {"cantidad": 3, "color": self.negro.pk}, follow=True)
        self.assertContains(r, "se vende desde 4 unidades")
        self.assertEqual(self.carrito()[self.clave(self.remera, self.negro)], 6)
        self.client.post(url, {"cantidad": 5, "color": self.negro.pk})
        self.assertEqual(self.carrito()[self.clave(self.remera, self.negro)], 5)

    def test_quitar_un_color_no_toca_los_otros(self):
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 4, self.blanco)
        self.client.post(
            reverse("pedidos:quitar", args=[self.remera.pk]), {"color": self.negro.pk}
        )
        self.assertEqual(list(self.carrito()), [self.clave(self.remera, self.blanco)])

    def test_las_claves_viejas_del_carrito_siguen_funcionando(self):
        sesion = self.client.session
        sesion["carrito"] = {str(self.short.pk): 3}
        sesion.save()
        r = self.client.get(reverse("pedidos:carrito"))
        self.assertContains(r, "Short")

    # --- pedido ---
    def test_el_pedido_guarda_color_talles_y_descuenta_el_stock_total(self):
        r = self.pedir()
        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse("pedidos:exito", args=[pedido.pk]))
        detalles = {d.color: d for d in pedido.detalles.all()}
        self.assertEqual(set(detalles), {"Negro", "Blanco"})
        self.assertEqual(detalles["Negro"].cantidad, 4)
        self.assertEqual(detalles["Blanco"].cantidad, 5)
        self.assertEqual(detalles["Negro"].talles, "2, 3, 4, 5")
        self.assertEqual(pedido.total, Decimal("9000"))
        self.remera.refresh_from_db()
        self.assertEqual(self.remera.stock, 11)

    def test_el_aviso_de_whatsapp_incluye_color_y_talles(self):
        self.pedir()
        texto = mensaje_pedido(Pedido.objects.get())
        self.assertIn("4 x Remera · Negro · talles 2, 3, 4, 5", texto)
        self.assertIn("5 x Remera · Blanco · talles 2, 3, 4, 5", texto)

    def test_confirmar_revalida_la_curva_si_cambiaron_los_talles(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.remera.talles.add(Talle.objects.get(nombre="1"))  # la curva pasa a 5
        r = self.client.post(reverse("pedidos:confirmar"), DATOS, follow=True)
        self.assertContains(r, "se vende desde 5 unidades por color")
        self.assertEqual(Pedido.objects.count(), 0)
        self.remera.refresh_from_db()
        self.assertEqual(self.remera.stock, 20)

    def test_confirmar_revalida_el_stock_compartido(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 4, self.blanco)
        Producto.objects.filter(pk=self.remera.pk).update(stock=6)
        r = self.client.post(reverse("pedidos:confirmar"), DATOS, follow=True)
        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(Pedido.objects.count(), 0)

    # --- catálogo ---
    def test_la_tarjeta_de_un_modelo_con_colores_lleva_a_la_ficha(self):
        r = self.client.get(reverse("catalogo:listado"))
        self.assertContains(r, "Elegir color")
        self.assertNotContains(r, reverse("pedidos:agregar", args=[self.remera.pk]))
        self.assertContains(r, reverse("pedidos:agregar", args=[self.short.pk]))

    def test_la_ficha_ofrece_elegir_color_y_arranca_en_la_curva(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.remera.pk]))
        self.assertContains(r, 'name="color"', count=2)
        self.assertContains(r, 'value="4" min="4"')