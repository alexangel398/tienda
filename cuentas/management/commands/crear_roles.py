from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from cuentas.services import ROL_ADMINISTRADOR, ROL_CLIENTE, ROL_COLABORADOR

ACCIONES = ["add", "change", "delete", "view"]


def permisos(app, modelos):
    codenames = [f"{accion}_{modelo}" for modelo in modelos for accion in ACCIONES]
    return list(
        Permission.objects.filter(
            content_type__app_label=app, codename__in=codenames
        )
    )


class Command(BaseCommand):
    help = "Crea los grupos Cliente, Colaborador y Administrador con sus permisos"

    def handle(self, *args, **options):
        catalogo = permisos("catalogo", ["categoria", "marca", "producto"])

        Group.objects.get_or_create(name=ROL_CLIENTE)

        colaborador, _ = Group.objects.get_or_create(name=ROL_COLABORADOR)
        colaborador.permissions.set(catalogo)

        administrador, _ = Group.objects.get_or_create(name=ROL_ADMINISTRADOR)
        administrador.permissions.set(catalogo + permisos("auth", ["user"]))

        self.stdout.write(self.style.SUCCESS("Roles creados."))