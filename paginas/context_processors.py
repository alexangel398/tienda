from urllib.parse import quote

from django.conf import settings

ENLACES = [
    {"texto": "Catálogo", "url": "catalogo:listado"},
    
    {"texto": "Contacto", "url": "paginas:contacto"},
]

REDES = [ ("Facebook", "facebook"), ("TikTok", "tiktok")]


def negocio(request):
    datos = settings.NEGOCIO
    inicio, _, final = datos["nombre"].rpartition(" ")
    mensaje = quote("Hola, quiero hacer una consulta.")
    return {
        "negocio": datos,
        "marca_inicio": inicio,
        "marca_final": final,
        "enlaces": ENLACES,
        "redes": [{"nombre": n, "url": datos[c]} for n, c in REDES if datos.get(c)],
        "whatsapp_url": f"https://wa.me/{datos['whatsapp']}?text={mensaje}",
    }