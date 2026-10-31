from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

LADO_MAXIMO = 1080
CALIDAD_WEBP = 80


def optimizar_imagen(archivo):
    """Devuelve la foto como WebP de hasta 1080 px por lado, lista para subir."""
    imagen = ImageOps.exif_transpose(Image.open(archivo))  # respeta la orientación del celular
    if imagen.mode in ("RGBA", "LA", "P"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        imagen = fondo
    else:
        imagen = imagen.convert("RGB")
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)

    salida = BytesIO()
    imagen.save(salida, format="WEBP", quality=CALIDAD_WEBP, method=6)
    return ContentFile(salida.getvalue(), name=f"{Path(archivo.name).stem}.webp")


def optimizar_campo(campo):
    """Optimiza una foto recién subida. Una ya guardada no se toca,
    así editar el precio o el nombre no la vuelve a comprimir."""
    if campo and not campo._committed:
        return optimizar_imagen(campo.file)
    return campo