from django.contrib.auth.models import Group

ROL_CLIENTE = "Cliente"
ROL_COLABORADOR = "Colaborador"
ROL_ADMINISTRADOR = "Administrador"


def asignar_rol_cliente(usuario):
    grupo, _ = Group.objects.get_or_create(name=ROL_CLIENTE)
    usuario.groups.add(grupo)