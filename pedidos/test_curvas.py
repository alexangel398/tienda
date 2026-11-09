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

    # --- ayudas ---
    def agregar(self, producto, cantidad, *colores):
        datos = {"cantidad": cantidad, "colores": [c.pk for c in colores]}
        return self.client.post(
            reverse("pedidos:agregar", args=[producto.pk]), datos, follow=True
        )

    def clave(self, producto, color=None):
        return f"{producto.pk}:{color.pk}" if color else str(producto.pk)

    def carrito(self):
        return self.client.session.get("carrito", {})

    def actualizar(self, producto, cantidad, color=None):
        datos = {"cantidad": cantidad}
        if color:
            datos["color"] = color.pk
        return self.client.post(
            reverse("pedidos:actualizar", args=[producto.pk]), datos, follow=True
        )

    # --- agregar desde la ficha ---
    def test_un_modelo_sin_colores_se_agrega_con_su_curva(self):
        r = self.agregar(self.short, 2)
        self.assertContains(r, "se vende desde 3 unidades en total")
        self.assertContains(r, "te faltan 1")
        self.assertEqual(self.carrito(), {})
        self.agregar(self.short, 3)
        self.assertEqual(self.carrito(), {self.clave(self.short): 3})

    def test_un_color_con_la_curva_completa(self):
        self.agregar(self.remera, 4, self.negro)
        self.assertEqual(self.carrito(), {self.clave(self.remera, self.negro): 4})

    def test_varios_colores_reparten_en_partes_iguales(self):
        self.agregar(self.remera, 4, self.negro, self.blanco)
        self.assertEqual(
            self.carrito(),
            {
                self.clave(self.remera, self.negro): 2,
                self.clave(self.remera, self.blanco): 2,
            },
        )

    def test_el_resto_va_al_primer_color_por_orden_alfabetico(self):
        self.agregar(self.remera, 5, self.negro, self.blanco)
        self.assertEqual(
            self.carrito(),
            {
                self.clave(self.remera, self.blanco): 3,
                self.clave(self.remera, self.negro): 2,
            },
        )

    def test_cuatro_colores_con_una_unidad_cada_uno(self):
        verde = Color.objects.get(nombre="Verde")
        self.remera.colores.add(self.rojo, verde)
        self.agregar(self.remera, 4, self.negro, self.blanco, self.rojo, verde)
        self.assertEqual(sorted(self.carrito().values()), [1, 1, 1, 1])

    def test_mas_colores_que_unidades_se_rechaza(self):
        extra = [Color.objects.get(nombre=n) for n in ("Rojo", "Verde", "Azul")]
        self.remera.colores.add(*extra)
        r = self.agregar(self.remera, 4, self.negro, self.blanco, *extra)
        self.assertContains(r, "Elegiste 5 colores y 4 unidades")
        self.assertEqual(self.carrito(), {})

    def test_el_color_es_opcional(self):
        self.agregar(self.remera, 4)
        self.assertEqual(self.carrito(), {self.clave(self.remera): 4})

    def test_un_color_que_no_es_del_modelo_se_rechaza(self):
        r = self.agregar(self.remera, 4, self.rojo)
        self.assertContains(r, "no está disponible en ese color")
        self.assertEqual(self.carrito(), {})

    def test_sin_unidades_pide_elegir_cuantas(self):
        r = self.agregar(self.remera, 0, self.negro)
        self.assertContains(r, "Elegí cuántas unidades querés")

    def test_se_pueden_sumar_unidades_sueltas_despues(self):
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 1, self.blanco)
        self.assertEqual(
            self.carrito(),
            {
                self.clave(self.remera, self.negro): 4,
                self.clave(self.remera, self.blanco): 1,
            },
        )

    def test_otro_modelo_no_completa_el_minimo(self):
        self.agregar(self.remera, 4, self.negro)
        r = self.agregar(self.short, 2)
        self.assertContains(r, "se vende desde 3 unidades en total")
        self.assertEqual(self.carrito(), {self.clave(self.remera, self.negro): 4})

    def test_el_stock_se_comparte_entre_los_colores(self):
        Producto.objects.filter(pk=self.remera.pk).update(stock=6)
        self.agregar(self.remera, 4, self.negro, self.blanco)
        r = self.agregar(self.remera, 3, self.negro)
        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(sum(self.carrito().values()), 4)

    # --- cambiar el carrito ---
    def test_actualizar_puede_dejar_el_modelo_por_debajo_y_el_carrito_avisa(self):
        self.agregar(self.remera, 4, self.negro, self.blanco)
        r = self.actualizar(self.remera, 1, self.negro)
        self.assertEqual(self.carrito()[self.clave(self.remera, self.negro)], 1)
        self.assertEqual(len(r.context["problemas"]), 1)
        self.assertContains(r, "te faltan 1")

    def test_actualizar_respeta_el_stock(self):
        Producto.objects.filter(pk=self.remera.pk).update(stock=5)
        self.agregar(self.remera, 4, self.negro)
        r = self.actualizar(self.remera, 6, self.negro)
        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(self.carrito()[self.clave(self.remera, self.negro)], 4)

    def test_quitar_una_linea_no_toca_las_otras(self):
        self.agregar(self.remera, 4, self.negro, self.blanco)
        r = self.client.post(
            reverse("pedidos:quitar", args=[self.remera.pk]),
            {"color": self.negro.pk},
            follow=True,
        )
        self.assertEqual(list(self.carrito()), [self.clave(self.remera, self.blanco)])
        self.assertContains(r, "te faltan 2")

    def test_las_claves_viejas_del_carrito_siguen_funcionando(self):
        sesion = self.client.session
        sesion["carrito"] = {str(self.short.pk): 3}
        sesion.save()
        r = self.client.get(reverse("pedidos:carrito"))
        self.assertContains(r, "Short")

    # --- confirmar el pedido ---
    def test_un_carrito_incompleto_no_se_puede_confirmar(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro, self.blanco)
        self.actualizar(self.remera, 1, self.negro)
        r = self.client.get(reverse("pedidos:confirmar"), follow=True)
        self.assertContains(r, "te faltan 1")
        self.client.post(reverse("pedidos:confirmar"), DATOS)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_el_pedido_guarda_color_color_a_coordinar_y_talles(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 1)
        r = self.client.post(reverse("pedidos:confirmar"), DATOS)

        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse("pedidos:exito", args=[pedido.pk]))
        detalles = {d.color: d for d in pedido.detalles.all()}
        self.assertEqual(set(detalles), {"Negro", "Color a coordinar"})
        self.assertEqual(detalles["Negro"].cantidad, 4)
        self.assertEqual(detalles["Color a coordinar"].cantidad, 1)
        self.assertEqual(detalles["Negro"].talles, "2, 3, 4, 5")
        self.assertEqual(pedido.total, Decimal("5000"))
        self.remera.refresh_from_db()
        self.assertEqual(self.remera.stock, 15)

    def test_un_modelo_sin_colores_no_guarda_color(self):
        self.client.force_login(self.usuario)
        self.agregar(self.short, 3)
        self.client.post(reverse("pedidos:confirmar"), DATOS)
        detalle = Pedido.objects.get().detalles.get()
        self.assertEqual(detalle.color, "")
        self.assertEqual(detalle.talles, "1, 2, 3")

    def test_el_ticket_de_whatsapp_incluye_color_y_talles(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.agregar(self.remera, 1)
        self.client.post(reverse("pedidos:confirmar"), DATOS)
        texto = mensaje_pedido(Pedido.objects.get())
        self.assertIn(
            "*Remera*\n   Talles: 2, 3, 4, 5\n   - 4 un. (Negro)\n   - 1 un. (A coordinar)\n   Subtotal: $5.000,00",
            texto,
        )

    def test_el_ticket_omite_color_y_talles_si_el_modelo_no_los_tiene(self):
        sin_variantes = Producto.objects.create(
            nombre="Cinto", precio=Decimal("500"), stock=5,
            categoria=self.remera.categoria, marca=self.remera.marca,
        )
        self.client.force_login(self.usuario)
        self.agregar(sin_variantes, 1)
        self.client.post(reverse("pedidos:confirmar"), DATOS)
        texto = mensaje_pedido(Pedido.objects.get())
        self.assertIn("*Cinto*\n   - 1 un. (Único)\n   Subtotal: $500,00", texto)
        self.assertNotIn("Talles:", texto)

    def test_confirmar_revalida_la_curva_si_cambiaron_los_talles(self):
        self.client.force_login(self.usuario)
        self.agregar(self.remera, 4, self.negro)
        self.remera.talles.add(Talle.objects.get(nombre="1"))  # la curva pasa a 5
        r = self.client.post(reverse("pedidos:confirmar"), DATOS, follow=True)
        self.assertContains(r, "te faltan 1")
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

    # --- catálogo y ficha ---
    def test_la_tarjeta_de_un_modelo_con_colores_lleva_a_la_ficha(self):
        r = self.client.get(reverse("catalogo:listado"))
        self.assertContains(r, "Elegir color")
        self.assertNotContains(r, reverse("pedidos:agregar", args=[self.remera.pk]))
        self.assertContains(r, reverse("pedidos:agregar", args=[self.short.pk]))

    def test_la_ficha_con_colores_muestra_bolitas_y_un_solo_selector(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.remera.pk]))
        self.assertContains(r, 'name="colores"', count=2)
        self.assertContains(r, 'class="bolita"', count=2)
        self.assertContains(r, 'value="4" min="4"')
        self.assertNotContains(r, "Sin elegir color")

    def test_la_ficha_sin_colores_arranca_en_la_curva(self):
        r = self.client.get(reverse("catalogo:detalle", args=[self.short.pk]))
        self.assertContains(r, 'value="3" min="3"')
        self.assertNotContains(r, 'name="colores"')