from django import forms

from .models import Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["entrega", "telefono", "direccion"]
        widgets = {"entrega": forms.RadioSelect}

    def clean(self):
        datos = super().clean()
        if datos.get("entrega") == Pedido.Entrega.ENVIO and not datos.get("direccion"):
            self.add_error("direccion", "Ingresá la dirección de envío.")
        return datos