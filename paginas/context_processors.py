from urllib.parse import quote

from django.conf import settings


def negocio(request):
    datos = settings.NEGOCIO
    mensaje = quote("Hola, quiero hacer una consulta.")
    return {
        "negocio": datos,
        "whatsapp_url": f"https://wa.me/{datos['whatsapp']}?text={mensaje}",
    }