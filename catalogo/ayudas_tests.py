import shutil
import tempfile
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

ALMACENAMIENTO = {
    **settings.STORAGES,
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}


def foto(nombre="foto.jpg", tamano=(3000, 2000), modo="RGB", formato="JPEG", color=(200, 60, 60)):
    buffer = BytesIO()
    Image.new(modo, tamano, color).save(buffer, format=formato)
    return SimpleUploadedFile(
        nombre, buffer.getvalue(), content_type=f"image/{formato.lower()}"
    )


class ArchivosTemporalesTestCase(TestCase):
    """Guarda los archivos subidos en una carpeta temporal y nunca en Cloudinary."""

    @classmethod
    def setUpClass(cls):
        cls._carpeta = tempfile.mkdtemp()
        cls._config = override_settings(MEDIA_ROOT=cls._carpeta, STORAGES=ALMACENAMIENTO)
        cls._config.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._config.disable()
        shutil.rmtree(cls._carpeta, ignore_errors=True)