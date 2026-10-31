from django import template

register = template.Library()


@register.filter
def optimizada(url, ancho=800):
    """Pide a Cloudinary formato automático, calidad automática y el ancho indicado."""
    marca = "/upload/"
    if "res.cloudinary.com" not in url or marca not in url:
        return url
    inicio, resto = url.split(marca, 1)
    if resto.startswith(("f_auto", "q_auto")):
        return url
    return f"{inicio}{marca}f_auto,q_auto,w_{int(ancho)}/{resto}"