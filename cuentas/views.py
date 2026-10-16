from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistroForm
from .services import asignar_rol_cliente


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            asignar_rol_cliente(usuario)
            login(request, usuario)
            return redirect("catalogo:listado")
    else:
        form = RegistroForm()
    return render(request, "cuentas/registro.html", {"form": form})