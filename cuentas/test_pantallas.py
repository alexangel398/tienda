from django.test import TestCase
from django.urls import reverse


class PantallasTests(TestCase):
    def test_registro_e_ingreso_cargan(self):
        for nombre in ["cuentas:registro", "cuentas:login"]:
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)