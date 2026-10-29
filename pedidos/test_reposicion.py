from django.contrib.auth.models import User
from django.urls import reverse

from .models import Pedido
from .services import cambiar_estado, reponer_stock
from .test_cobertura import BaseTests, CLAVE, Estado


class ReposicionAlBorrarTests(BaseTests):
    def test_borrar_un_pedido_pendiente_repone_el_stock(self):
        self.pedido_con_detalle(Estado.PENDIENTE).delete()
        self.assertEqual(self.stock(), 5)

    def test_borrar_un_pedido_preparado_repone_el_stock(self):
        self.pedido_con_detalle(Estado.PREPARADO).delete()
        self.assertEqual(self.stock(), 5)

    def test_borrar_un_pedido_cancelado_no_repone_dos_veces(self):
        pedido = self.pedido_con_detalle()
        cambiar_estado(pedido, Estado.CANCELADO)
        self.assertEqual(self.stock(), 5)
        # El objeto en memoria sigue diciendo "pendiente": el signal lee el estado real.
        pedido.delete()
        self.assertEqual(self.stock(), 5)

    def test_borrar_un_pedido_entregado_no_repone(self):
        self.pedido_con_detalle(Estado.ENTREGADO).delete()
        self.assertEqual(self.stock(), 3)

    def test_borrar_varios_pedidos_a_la_vez_repone_cada_uno(self):
        self.pedido_con_detalle(cantidad=2)
        self.pedido_con_detalle(cantidad=1)
        self.producto.__class__.objects.filter(pk=self.producto.pk).update(stock=2)
        Pedido.objects.all().delete()
        self.assertEqual(self.stock(), 5)

    def test_reponer_stock_suma_las_cantidades_del_pedido(self):
        pedido = self.pedido_con_detalle(cantidad=3)
        reponer_stock(pedido)
        self.assertEqual(self.stock(), 5)

    def test_el_panel_no_permite_borrar_pedidos_ni_a_un_superusuario(self):
        pedido = self.pedido_con_detalle()
        self.client.force_login(User.objects.create_superuser("root", password=CLAVE))

        r = self.client.post(
            reverse("admin:pedidos_pedido_delete", args=[pedido.pk]), {"post": "yes"}
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())
        self.assertEqual(self.stock(), 3)

        listado = self.client.get(reverse("admin:pedidos_pedido_changelist"))
        self.assertNotContains(listado, "delete_selected")