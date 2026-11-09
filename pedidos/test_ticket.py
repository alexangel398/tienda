from decimal import Decimal

from django.test import SimpleTestCase

from .models import DetallePedido
from .services import formato_pesos, mensaje_pedido, url_whatsapp
from .test_cobertura import BaseTests

# Tope prudente que fijé yo para el enlace completo; no es un límite oficial de WhatsApp.
LIMITE_URL = 3500


class FormatoPesosTests(SimpleTestCase):
    def test_formato_argentino(self):
        self.assertEqual(formato_pesos(Decimal("200000")), "$200.000,00")
        self.assertEqual(formato_pesos(Decimal("460000")), "$460.000,00")
        self.assertEqual(formato_pesos(Decimal("1234567.5")), "$1.234.567,50")
        self.assertEqual(formato_pesos(Decimal("999.99")), "$999,99")
        self.assertEqual(formato_pesos(0), "$0,00")


class LargoDelTicketTests(BaseTests):
    def test_un_pedido_grande_entra_en_un_enlace_de_whatsapp(self):
        pedido = self.pedido_con_detalle(cantidad=4)
        for color in ["Negro", "Blanco", "Rojo", "Azul", "Verde", "Gris", "Beige"]:
            DetallePedido.objects.create(
                pedido=pedido, producto=self.producto, cantidad=5,
                precio_unitario=self.producto.precio, color=color,
                talles="1, 2, 3, 4, 5",
            )
        url = url_whatsapp("5491112345678", mensaje_pedido(pedido))
        self.assertLess(len(url), LIMITE_URL)