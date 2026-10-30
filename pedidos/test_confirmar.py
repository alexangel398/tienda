from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

from .models import Pedido

CLAVE = "Clave-segura-2026"
DATOS = {"entrega": "retiro", "telefono": "1155551234"}


class ConfirmarPedidoTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        self.producto = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )
        self.usuario = User.objects.create_user("ana", password=CLAVE)
        self.url = reverse("pedidos:confirmar")

    def cargar_carrito(self, cantidad):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]),
            {"cantidad": cantidad},
        )

    def test_requiere_iniciar_sesion(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, f"{reverse('cuentas:login')}?next={self.url}")

    def test_carrito_vacio_vuelve_al_carrito(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("pedidos:carrito"))

    def test_pedido_exitoso_descuenta_stock_y_vacia_el_carrito(self):
        self.client.force_login(self.usuario)
        self.cargar_carrito(2)
        r = self.client.post(self.url, DATOS)

        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse("pedidos:exito", args=[pedido.pk]))
        self.assertEqual(pedido.cliente, self.usuario)
        self.assertEqual(pedido.total, Decimal("3000"))
        self.assertEqual(pedido.detalles.get().precio_unitario, Decimal("1500"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)
        self.assertEqual(self.client.session["carrito"], {})

    def test_stock_insuficiente_no_crea_pedido_ni_descuenta(self):
        self.client.force_login(self.usuario)
        self.cargar_carrito(3)
        Producto.objects.filter(pk=self.producto.pk).update(stock=1)

        r = self.client.post(self.url, DATOS, follow=True)

        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(Pedido.objects.count(), 0)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)

    def test_el_envio_no_pide_direccion_porque_se_coordina_por_whatsapp(self):
        self.client.force_login(self.usuario)
        self.cargar_carrito(1)
        r = self.client.post(self.url, {**DATOS, "entrega": "envio"})

        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse("pedidos:exito", args=[pedido.pk]))
        self.assertEqual(pedido.entrega, Pedido.Entrega.ENVIO)

    def test_un_cliente_no_ve_el_pedido_de_otro(self):
        self.client.force_login(self.usuario)
        self.cargar_carrito(1)
        self.client.post(self.url, DATOS)
        pedido = Pedido.objects.get()

        otro = User.objects.create_user("beto", password=CLAVE)
        self.client.force_login(otro)
        r = self.client.get(reverse("pedidos:exito", args=[pedido.pk]))
        self.assertEqual(r.status_code, 404)