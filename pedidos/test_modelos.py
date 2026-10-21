from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from cuentas.services import ROL_COLABORADOR

from .models import DetallePedido, Pedido


class PedidoModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("crear_roles", verbosity=0)
        cls.cliente = User.objects.create_user("ana", password="Clave-segura-2026")
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        cls.producto = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )

    def test_pedido_nuevo_queda_pendiente(self):
        pedido = Pedido.objects.create(cliente=self.cliente, telefono="1155551234")
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)

    def test_detalle_calcula_subtotal_con_el_precio_copiado(self):
        pedido = Pedido.objects.create(cliente=self.cliente, telefono="1155551234")
        detalle = DetallePedido.objects.create(
            pedido=pedido, producto=self.producto,
            cantidad=2, precio_unitario=self.producto.precio,
        )
        self.producto.precio = Decimal("9999")
        self.producto.save()
        detalle.refresh_from_db()
        self.assertEqual(detalle.subtotal, Decimal("3000"))

    def test_colaborador_ve_pedidos_pero_no_los_crea(self):
        colab = User.objects.create_user(
            "colab", password="Clave-segura-2026", is_staff=True
        )
        colab.groups.add(Group.objects.get(name=ROL_COLABORADOR))
        self.client.force_login(colab)
        self.assertEqual(
            self.client.get(reverse("admin:pedidos_pedido_changelist")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("admin:pedidos_pedido_add")).status_code, 403
        )