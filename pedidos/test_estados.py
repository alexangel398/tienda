from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from catalogo.models import Categoria, Marca, Producto

from .admin import PedidoAdmin
from .models import DetallePedido, Pedido
from .services import TransicionInvalida, cambiar_estado

Estado = Pedido.Estado


class FormFalso:
    """Imita lo que le llega a save_model cuando se edita el estado."""

    changed_data = ["estado"]
    initial = {"estado": Estado.PENDIENTE}


class EstadosTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        self.producto = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )
        cliente = User.objects.create_user("ana", password="Clave-segura-2026")
        self.pedido = Pedido.objects.create(
            cliente=cliente, telefono="1155551111", total=Decimal("3000")
        )
        DetallePedido.objects.create(
            pedido=self.pedido, producto=self.producto,
            cantidad=2, precio_unitario=Decimal("1500"),
        )
        # El pedido ya descontó 2 unidades: quedan 3 en stock.
        Producto.objects.filter(pk=self.producto.pk).update(stock=3)

    def stock(self):
        self.producto.refresh_from_db()
        return self.producto.stock

    def test_flujo_normal_pendiente_preparado_entregado(self):
        cambiar_estado(self.pedido, Estado.PREPARADO)
        pedido = cambiar_estado(self.pedido, Estado.ENTREGADO)
        self.assertEqual(pedido.estado, Estado.ENTREGADO)
        self.assertEqual(self.stock(), 3)

    def test_cancelar_repone_el_stock(self):
        pedido = cambiar_estado(self.pedido, Estado.CANCELADO)
        self.assertEqual(pedido.estado, Estado.CANCELADO)
        self.assertEqual(self.stock(), 5)

    def test_cancelar_dos_veces_no_repone_dos_veces(self):
        cambiar_estado(self.pedido, Estado.CANCELADO)
        cambiar_estado(self.pedido, Estado.CANCELADO)
        self.assertEqual(self.stock(), 5)

    def test_un_pedido_entregado_no_se_puede_cancelar(self):
        cambiar_estado(self.pedido, Estado.PREPARADO)
        cambiar_estado(self.pedido, Estado.ENTREGADO)
        with self.assertRaises(TransicionInvalida):
            cambiar_estado(self.pedido, Estado.CANCELADO)
        self.assertEqual(self.stock(), 3)

    def test_no_se_puede_saltar_estados(self):
        with self.assertRaises(TransicionInvalida):
            cambiar_estado(self.pedido, Estado.ENTREGADO)

    def test_el_admin_cancela_desde_el_formulario_y_repone_stock(self):
        modelo_admin = PedidoAdmin(Pedido, admin.site)
        self.pedido.estado = Estado.CANCELADO  # lo que llega del formulario
        modelo_admin.save_model(
            RequestFactory().post("/"), self.pedido, FormFalso(), change=True
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.CANCELADO)
        self.assertEqual(self.stock(), 5)