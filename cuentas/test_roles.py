from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .services import ROL_ADMINISTRADOR, ROL_CLIENTE, ROL_COLABORADOR

CLAVE = "Clave-segura-2026"


def crear_usuario(nombre, rol, staff=False):
    usuario = User.objects.create_user(nombre, password=CLAVE, is_staff=staff)
    usuario.groups.add(Group.objects.get(name=rol))
    return usuario


class RolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("crear_roles", verbosity=0)
        cls.productos = reverse("admin:catalogo_producto_changelist")
        cls.usuarios = reverse("admin:auth_user_changelist")

    def test_comando_crea_los_tres_grupos(self):
        nombres = set(Group.objects.values_list("name", flat=True))
        self.assertEqual(nombres, {ROL_CLIENTE, ROL_COLABORADOR, ROL_ADMINISTRADOR})

    def test_registro_asigna_rol_cliente(self):
        self.client.post(
            reverse("cuentas:registro"),
            {
                "username": "ana",
                "email": "ana@example.com",
                "password1": CLAVE,
                "password2": CLAVE,
            },
        )
        usuario = User.objects.get(username="ana")
        self.assertTrue(usuario.groups.filter(name=ROL_CLIENTE).exists())

    def test_colaborador_gestiona_catalogo_pero_no_usuarios(self):
        self.client.force_login(crear_usuario("colab", ROL_COLABORADOR, staff=True))
        self.assertEqual(self.client.get(self.productos).status_code, 200)
        self.assertEqual(self.client.get(self.usuarios).status_code, 403)

    def test_administrador_gestiona_catalogo_y_usuarios(self):
        self.client.force_login(crear_usuario("admin2", ROL_ADMINISTRADOR, staff=True))
        self.assertEqual(self.client.get(self.productos).status_code, 200)
        self.assertEqual(self.client.get(self.usuarios).status_code, 200)

    def test_cliente_no_entra_al_panel(self):
        self.client.force_login(crear_usuario("cliente1", ROL_CLIENTE))
        self.assertEqual(self.client.get(self.productos).status_code, 302)