from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from . import imagenes
from .ayudas_tests import ArchivosTemporalesTestCase, foto
from .imagenes import LADO_MAXIMO, optimizar_imagen
from .models import Categoria, Marca, Producto
from .templatetags.fotos import optimizada


class OptimizarImagenTests(SimpleTestCase):
    def test_convierte_a_webp_y_limita_el_tamano(self):
        resultado = optimizar_imagen(foto(tamano=(3000, 2000)))
        imagen = Image.open(resultado)
        self.assertEqual(imagen.format, "WEBP")
        self.assertEqual(imagen.size, (1080, 720))
        self.assertTrue(resultado.name.endswith(".webp"))

    def test_no_agranda_las_fotos_chicas(self):
        imagen = Image.open(optimizar_imagen(foto(tamano=(400, 300))))
        self.assertEqual(imagen.size, (400, 300))

    def test_la_transparencia_se_vuelve_fondo_blanco(self):
        archivo = foto("logo.png", (200, 200), "RGBA", "PNG", (0, 0, 0, 0))
        imagen = Image.open(optimizar_imagen(archivo))
        self.assertEqual(imagen.mode, "RGB")
        self.assertTrue(all(canal > 240 for canal in imagen.getpixel((5, 5))))

    def test_respeta_la_orientacion_del_celular(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # foto girada 90 grados
        buffer = BytesIO()
        Image.new("RGB", (300, 200), (10, 10, 10)).save(buffer, format="JPEG", exif=exif)
        archivo = SimpleUploadedFile("giro.jpg", buffer.getvalue(), content_type="image/jpeg")
        self.assertEqual(Image.open(optimizar_imagen(archivo)).size, (200, 300))


class ProductoImagenTests(ArchivosTemporalesTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre="Ropa")
        cls.marca = Marca.objects.create(nombre="Lacoste")

    def crear(self, **extra):
        return Producto.objects.create(
            nombre="Remera", precio=5000, stock=3,
            categoria=self.categoria, marca=self.marca, **extra,
        )

    def test_una_foto_nueva_se_guarda_optimizada(self):
        producto = self.crear(imagen=foto())
        self.assertTrue(producto.imagen.name.endswith(".webp"))
        with producto.imagen.open() as archivo:
            self.assertLessEqual(max(Image.open(archivo).size), LADO_MAXIMO)

    def test_editar_otros_datos_no_vuelve_a_comprimir(self):
        producto = self.crear(imagen=foto())
        nombre = producto.imagen.name
        with patch.object(imagenes, "optimizar_imagen", wraps=optimizar_imagen) as espia:
            producto.precio = 6000
            producto.save()
            producto = Producto.objects.get(pk=producto.pk)
            producto.stock = 1
            producto.save()
        espia.assert_not_called()
        self.assertEqual(Producto.objects.get(pk=producto.pk).imagen.name, nombre)

    def test_reemplazar_la_foto_si_la_procesa(self):
        producto = self.crear(imagen=foto("a.jpg"))
        primera = producto.imagen.name
        producto.imagen = foto("b.jpg")
        producto.save()
        self.assertNotEqual(producto.imagen.name, primera)
        self.assertTrue(producto.imagen.name.endswith(".webp"))

    def test_un_producto_sin_foto_se_guarda_normalmente(self):
        self.assertFalse(self.crear().imagen)


class FiltroOptimizadaTests(SimpleTestCase):
    url = "https://res.cloudinary.com/demo/image/upload/v1/media/productos/remera.webp"

    def test_inyecta_los_parametros_de_cloudinary(self):
        self.assertEqual(
            optimizada(self.url),
            "https://res.cloudinary.com/demo/image/upload/f_auto,q_auto,w_800/v1/media/productos/remera.webp",
        )

    def test_acepta_otro_ancho(self):
        self.assertIn("w_1080", optimizada(self.url, 1080))

    def test_no_modifica_las_urls_locales(self):
        self.assertEqual(optimizada("/media/productos/x.webp"), "/media/productos/x.webp")

    def test_no_repite_los_parametros(self):
        self.assertEqual(optimizada(optimizada(self.url)), optimizada(self.url))