import re

from django import forms

from .models import Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["entrega", "telefono", "direccion"]
        widgets = {"entrega": forms.RadioSelect}
        help_texts = {
            "telefono": "Con código de área, sin 0 ni 15. Ejemplo: 1155551234. Lo usamos para coordinar tu pedido por WhatsApp."
        }

    def clean_telefono(self):
        digitos = re.sub(r"\D", "", self.cleaned_data["telefono"])
        if len(digitos) != 10:
            raise forms.ValidationError(
                "Ingresá el código de área y el número, sin 0 ni 15 (10 dígitos). Ejemplo: 1155551234."
            )
        return digitos

    def clean(self):
        datos = super().clean()
        if datos.get("entrega") == Pedido.Entrega.ENVIO and not datos.get("direccion"):
            self.add_error("direccion", "Ingresá la dirección de envío.")
        return datos