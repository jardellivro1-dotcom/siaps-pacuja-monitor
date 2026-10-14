import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app
from siaps.models import init_db
from siaps.services import create_improvement_action


class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.raw_dir = Path(self.temp_dir.name) / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(self.temp_dir.name) / "test.db"
        init_db(self.db_path)

        self.app = create_app({
            "TESTING": True,
            "RAW_DATA_DIR": self.raw_dir,
            "DB_PATH": self.db_path,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["status"], "ok")

    def test_methodology_endpoint(self):
        res = self.client.get("/api/methodology")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Nota Técnica nº 8/2026", res.json["metodologia"]["documento"])
        self.assertIn("eSF", res.json["indicadores"])
        self.assertIn("eMulti", res.json["indicadores"])

    def test_improvement_actions_crud(self):
        # 1. List initial (empty)
        res = self.client.get("/api/actions")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json["actions"]), 0)

        # 2. Create action
        payload = {
            "title": "Aumentar busca ativa de crianças para consulta C2",
            "description": "Focar nas crianças menores de 2 anos para melhorar indicador C2.",
            "team_type": "eSF",
            "indicator_code": "C2",
            "indicator_name": "Desenvolvimento Infantil",
            "responsible": "Coordenação da APS",
            "deadline": "2026-11-30",
            "status": "pendente",
        }
        res = self.client.post("/api/actions", json=payload)
        self.assertEqual(res.status_code, 201)
        action_id = res.json["id"]

        # 3. List contains newly created action
        res = self.client.get("/api/actions")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json["actions"]), 1)
        self.assertEqual(res.json["actions"][0]["id"], action_id)
        self.assertEqual(res.json["actions"][0]["responsible"], "Coordenação da APS")

        # 4. Update action status
        res = self.client.put(f"/api/actions/{action_id}", json={"status": "em_andamento"})
        self.assertEqual(res.status_code, 200)

        # Verify update
        res = self.client.get(f"/api/actions?status=em_andamento")
        self.assertEqual(len(res.json["actions"]), 1)

        # 5. Delete action
        res = self.client.delete(f"/api/actions/{action_id}")
        self.assertEqual(res.status_code, 200)

        # Verify deletion
        res = self.client.get("/api/actions")
        self.assertEqual(len(res.json["actions"]), 0)

    def test_raw_files_endpoint_and_download_security(self):
        # Create a dummy CSV in raw_dir
        test_file = self.raw_dir / "teste_seguranca.csv"
        test_file.write_text("dummy", encoding="utf-8")

        res = self.client.get("/api/raw-files/teste_seguranca.csv/download")
        self.assertEqual(res.status_code, 200)
        res.close()

        # Path traversal attack must be blocked (404)
        res_traversal = self.client.get("/api/raw-files/../../app.py/download")
        self.assertEqual(res_traversal.status_code, 404)
        res_traversal.close()

    def test_relatorio_view_and_api(self):
        res = self.client.get("/relatorio")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Relatório Executivo", res.text)

        res_api = self.client.get("/api/relatorio")
        self.assertEqual(res_api.status_code, 200)
        self.assertEqual(res_api.json["municipality"], "Pacujá")
        self.assertIn("counts_by_concept", res_api.json)

    def test_monthly_tracking_endpoint(self):
        res = self.client.get("/api/monthly-tracking")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["status"], "ativo")
        self.assertIn("next_scheduled_check", res.json)


if __name__ == "__main__":
    unittest.main()
