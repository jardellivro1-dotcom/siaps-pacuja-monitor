import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app


class AppShellTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "RAW_DATA_DIR": Path(self.temp_dir.name) / "raw",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_dashboard_starts_without_fabricated_results(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Aguardando os relatórios públicos de Pacujá".encode(), response.data)

    def test_status_reports_empty_dataset(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["municipality"], "Pacujá")
        self.assertEqual(response.json["state"], "CE")
        self.assertEqual(response.json["reports_count"], 0)
        self.assertEqual(response.json["status"], "aguardando_dados")


if __name__ == "__main__":
    unittest.main()
