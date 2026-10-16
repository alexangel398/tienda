from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

CLAVE = "Clave-segura-2026"


class CuentasTests(TestCase):
    datos = {
        "username": "ana",
        "email": "ana@example.com",
        "password1": CLAVE,
        "password2": CLAVE,
    }

    def test_registro_crea_usuario_y_abre_sesion(self):
        r = self.client.post(reverse("cuentas:registro"), self.datos)
        self.assertRedirects(r, reverse("catalogo:listado"))
        self.assertTrue(User.objects.filter(username="ana").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_contrasena_se_guarda_cifrada(self):
        self.client.post(reverse("cuentas:registro"), self.datos)
        usuario = User.objects.get(username="ana")
        self.assertNotEqual(usuario.password, CLAVE)
        self.assertTrue(usuario.check_password(CLAVE))

    def test_registro_con_contrasenas_distintas_falla(self):
        datos = {**self.datos, "password2": "otra-clave"}
        r = self.client.post(reverse("cuentas:registro"), datos)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="ana").exists())

    def test_inicio_y_cierre_de_sesion(self):
        User.objects.create_user("ana", password=CLAVE)
        r = self.client.post(
            reverse("cuentas:login"), {"username": "ana", "password": CLAVE}
        )
        self.assertRedirects(r, reverse("catalogo:listado"))
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("cuentas:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)