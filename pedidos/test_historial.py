from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

from .models import DetallePedido, Pedido

CLAVE = "Clave-segura-2026"


class HistorialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nombre="Insumos")
        marca = Marca.objects.create(nombre="Alfa")
        producto = Producto.objects.create(
            nombre="Cinta", precio=Decimal("1500"), stock=5,
            categoria=categoria, marca=marca,
        )
        cls.ana = User.objects.create_user("ana", password=CLAVE)
        cls.beto = User.objects.create_user("beto", password=CLAVE)

        cls.pedido_ana = Pedido.objects.create(
            cliente=cls.ana, telefono="1155551111", total=Decimal("3000")
        )
        DetallePedido.objects.create(
            pedido=cls.pedido_ana, producto=producto,
            cantidad=2, precio_unitario=Decimal("1500"),
        )
        cls.pedido_beto = Pedido.objects.create(
            cliente=cls.beto, telefono="1155552222", total=Decimal("1500")
        )

    def test_requiere_iniciar_sesion(self):
        url = reverse("pedidos:mis_pedidos")
        r = self.client.get(url)
        self.assertRedirects(r, f"{reverse('cuentas:login')}?next={url}")

    def test_lista_solo_los_pedidos_propios(self):
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:mis_pedidos"))
        self.assertEqual(list(r.context["pedidos"]), [self.pedido_ana])

    def test_detalle_muestra_estado_y_productos(self):
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:detalle", args=[self.pedido_ana.pk]))
        self.assertContains(r, "Cinta")
        self.assertContains(r, "Pendiente")

    def test_no_se_puede_ver_el_pedido_de_otro_cliente(self):
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:detalle", args=[self.pedido_beto.pk]))
        self.assertEqual(r.status_code, 404)

    def test_el_cambio_de_estado_se_refleja_en_el_historial(self):
        self.pedido_ana.estado = Pedido.Estado.ENTREGADO
        self.pedido_ana.save()
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:mis_pedidos"))
        self.assertContains(r, "Entregado")