from datetime import timedelta

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import PedidoForm
from .models import Pedido
from .services import mensaje_pedido, telefono_internacional, url_whatsapp
from .test_cobertura import CLAVE, BaseTests, Estado

NEGOCIO = {
    "nombre": "Mi Negocio",
    "ciudad": "Rosario",
    "whatsapp": "5491163633835",
    "direccion": "Calle Falsa 123",
    "horarios": "Lunes a viernes",
}


@override_settings(NEGOCIO=NEGOCIO)
class AvisoAlDuenoTests(BaseTests):
    def test_el_mensaje_incluye_el_detalle_del_pedido(self):
        pedido = self.pedido_con_detalle(cantidad=2)
        texto = mensaje_pedido(pedido)
        self.assertIn(f"pedido #{pedido.pk} en Mi Negocio", texto)
        self.assertIn("2 x Cinta ($3000.00)", texto)
        self.assertIn("Total: $3000.00", texto)
        self.assertIn("Entrega: Retiro en el local", texto)
        self.assertIn("Teléfono: 1155551111", texto)
        self.assertIn("Cliente: ana", texto)

    def test_el_mensaje_incluye_la_direccion_si_hay_envio(self):
        pedido = self.pedido_con_detalle()
        pedido.direccion = "Calle 1"
        pedido.save()
        self.assertIn("Dirección: Calle 1", mensaje_pedido(pedido))

    def test_la_url_de_whatsapp_codifica_el_mensaje(self):
        self.assertEqual(
            url_whatsapp("5491163633835", "Hola mundo"),
            "https://wa.me/5491163633835?text=Hola%20mundo",
        )

    def test_la_pantalla_de_exito_ofrece_enviar_el_pedido_por_whatsapp(self):
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 2}
        )
        r = self.client.post(
            reverse("pedidos:confirmar"),
            {"entrega": "retiro", "telefono": "1155551234"},
            follow=True,
        )
        self.assertContains(r, "Enviar mi pedido por WhatsApp")
        self.assertContains(r, "https://wa.me/5491163633835?text=")


class TelefonoTests(BaseTests):
    def test_conversion_al_formato_internacional(self):
        self.assertEqual(telefono_internacional("1155551234"), "5491155551234")
        self.assertEqual(telefono_internacional("01155551234"), "5491155551234")
        self.assertEqual(telefono_internacional("5491155551234"), "5491155551234")

    def test_el_formulario_acepta_y_limpia_el_telefono(self):
        form = PedidoForm({"entrega": "retiro", "telefono": "11 5555-1234"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["telefono"], "1155551234")

    def test_el_formulario_rechaza_telefonos_con_0_o_15(self):
        form = PedidoForm({"entrega": "retiro", "telefono": "011 15 5555 1234"})
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)


@override_settings(NEGOCIO=NEGOCIO)
class PanelDuenoTests(BaseTests):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_superuser("root", password=CLAVE))
        self.lista = reverse("admin:pedidos_pedido_changelist")

    def accion(self, nombre, pedido):
        return self.client.post(
            self.lista,
            {"action": nombre, "_selected_action": [pedido.pk]},
            follow=True,
        )

    def test_el_inicio_del_panel_avisa_los_pedidos_pendientes(self):
        self.pedido_con_detalle()
        r = self.client.get("/admin/")
        self.assertContains(r, "1")
        self.assertContains(r, "pedido pendiente")
        self.assertContains(r, "estado__exact=pendiente")

    def test_sin_pendientes_el_panel_no_avisa(self):
        self.pedido_con_detalle(Estado.ENTREGADO)
        r = self.client.get("/admin/")
        self.assertNotContains(r, "por atender")

    def test_el_listado_ofrece_whatsapp_al_cliente(self):
        self.pedido_con_detalle()
        r = self.client.get(self.lista)
        self.assertContains(r, "https://wa.me/5491155551111?text=")

    def test_un_pendiente_con_demora_se_marca_como_sin_atender(self):
        pedido = self.pedido_con_detalle()
        reciente = self.client.get(self.lista)
        self.assertNotContains(reciente, "sin atender")
        Pedido.objects.filter(pk=pedido.pk).update(
            fecha=timezone.now() - timedelta(days=3)
        )
        r = self.client.get(self.lista)
        self.assertContains(r, "sin atender")

    def test_las_acciones_marcan_preparado_y_entregado(self):
        pedido = self.pedido_con_detalle()
        r = self.accion("marcar_preparado", pedido)
        self.assertContains(r, "1 pedido(s) marcado(s) como preparado(s)")
        r = self.accion("marcar_entregado", pedido)
        self.assertContains(r, "1 pedido(s) marcado(s) como entregado(s)")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Estado.ENTREGADO)

    def test_entregar_un_pedido_pendiente_avisa_del_error(self):
        pedido = self.pedido_con_detalle()
        r = self.accion("marcar_entregado", pedido)
        self.assertContains(r, "No se puede pasar de Pendiente a Entregado")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Estado.PENDIENTE)