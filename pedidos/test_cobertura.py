from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

from .admin import PedidoAdmin
from .models import DetallePedido, Pedido
from .services import Carrito, crear_pedido

CLAVE = "Clave-segura-2026"
Estado = Pedido.Estado


class FormFalso:
    """Imita lo que le llega a save_model cuando se edita el estado."""

    def __init__(self, estado_inicial):
        self.changed_data = ["estado"]
        self.initial = {"estado": estado_inicial}


class BaseTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        self.producto = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )
        self.cliente = User.objects.create_user("ana", password=CLAVE)

    def pedido_con_detalle(self, estado=Estado.PENDIENTE, cantidad=2):
        pedido = Pedido.objects.create(
            cliente=self.cliente, telefono="1155551111",
            total=self.producto.precio * cantidad, estado=estado,
        )
        DetallePedido.objects.create(
            pedido=pedido, producto=self.producto,
            cantidad=cantidad, precio_unitario=self.producto.precio,
        )
        Producto.objects.filter(pk=self.producto.pk).update(stock=5 - cantidad)
        return pedido

    def stock(self):
        self.producto.refresh_from_db()
        return self.producto.stock


class CarritoServicioTests(BaseTests):
    def carrito(self):
        request = RequestFactory().get("/")
        request.session = SessionStore()
        return Carrito(request)

    def test_actualizar_con_cantidad_cero_quita_el_producto(self):
        carrito = self.carrito()
        carrito.agregar(self.producto, 2)
        self.assertTrue(carrito.actualizar(self.producto, 0))
        self.assertEqual(len(carrito), 0)

    def test_actualizar_por_encima_del_stock_no_cambia_nada(self):
        carrito = self.carrito()
        carrito.agregar(self.producto, 2)
        self.assertFalse(carrito.actualizar(self.producto, 6))
        self.assertEqual(len(carrito), 2)

    def test_un_producto_borrado_se_ignora_en_el_carrito(self):
        carrito = self.carrito()
        carrito.agregar(self.producto, 1)
        self.producto.delete()
        self.assertEqual(list(carrito), [])

    def test_crear_pedido_con_carrito_vacio_falla(self):
        datos = {"entrega": "retiro", "telefono": "1155551111"}
        with self.assertRaises(ValueError):
            crear_pedido(self.carrito(), self.cliente, datos)
        self.assertEqual(Pedido.objects.count(), 0)


class VistasTests(BaseTests):
    def test_actualizar_por_encima_del_stock_muestra_error(self):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 1}
        )
        r = self.client.post(
            reverse("pedidos:actualizar", args=[self.producto.pk]),
            {"cantidad": 6},
            follow=True,
        )
        self.assertContains(r, "No hay stock suficiente")
        self.assertEqual(self.client.session["carrito"][str(self.producto.pk)], 1)

    def test_confirmar_muestra_el_formulario_con_el_carrito(self):
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 2}
        )
        r = self.client.get(reverse("pedidos:confirmar"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Confirmar pedido")
        self.assertContains(r, "Cinta")


class ModelosTests(BaseTests):
    def test_textos_de_los_modelos(self):
        pedido = self.pedido_con_detalle()
        self.assertEqual(str(pedido), f"Pedido #{pedido.pk}")
        self.assertEqual(str(pedido.detalles.get()), "2 x Cinta")


class AdminPedidosTests(BaseTests):
    def setUp(self):
        super().setUp()
        root = User.objects.create_superuser("root", password=CLAVE)
        self.client.force_login(root)

    def test_la_pagina_de_un_pedido_carga_con_su_detalle(self):
        pedido = self.pedido_con_detalle()
        r = self.client.get(reverse("admin:pedidos_pedido_change", args=[pedido.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cinta")

    def test_la_accion_cancelar_repone_el_stock(self):
        pedido = self.pedido_con_detalle()
        r = self.client.post(
            reverse("admin:pedidos_pedido_changelist"),
            {"action": "cancelar", "_selected_action": [pedido.pk]},
            follow=True,
        )
        self.assertContains(r, "1 pedido(s) cancelado(s)")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Estado.CANCELADO)
        self.assertEqual(self.stock(), 5)

    def test_la_accion_cancelar_avisa_si_el_pedido_ya_fue_entregado(self):
        pedido = self.pedido_con_detalle(estado=Estado.ENTREGADO)
        r = self.client.post(
            reverse("admin:pedidos_pedido_changelist"),
            {"action": "cancelar", "_selected_action": [pedido.pk]},
            follow=True,
        )
        self.assertContains(r, "No se puede pasar de Entregado a Cancelado")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Estado.ENTREGADO)
        self.assertEqual(self.stock(), 3)

    def test_cambio_invalido_desde_el_formulario_muestra_error(self):
        pedido = self.pedido_con_detalle(estado=Estado.ENTREGADO)
        pedido.estado = Estado.CANCELADO  # lo que llega del formulario
        request = RequestFactory().post("/")
        request.session = SessionStore()
        request._messages = FallbackStorage(request)

        PedidoAdmin(Pedido, admin.site).save_model(
            request, pedido, FormFalso(Estado.ENTREGADO), change=True
        )

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Estado.ENTREGADO)
        mensajes = [str(m) for m in get_messages(request)]
        self.assertTrue(any("No se puede pasar" in m for m in mensajes))
        self.assertEqual(self.stock(), 3)