from django.test import TestCase
from django.urls import reverse


class SaludTests(TestCase):
    def test_responde_ok_en_texto_plano(self):
        r = self.client.get(reverse("paginas:salud"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"OK")
        self.assertTrue(r["Content-Type"].startswith("text/plain"))

    def test_no_consulta_la_base_de_datos(self):
        with self.assertNumQueries(0):
            self.client.get("/health/")

    def test_acepta_head_y_rechaza_post(self):
        self.assertEqual(self.client.head("/health/").status_code, 200)
        self.assertEqual(self.client.post("/health/").status_code, 405)