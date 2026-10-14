"""
Testes de segurança, validação de entradas, controle de concorrência e autorização.
Em conformidade com as diretrizes OWASP ASVS e regras do AGENTS.md.
"""

import os
import unittest
from unittest.mock import patch

from app import app
from siaps.security import SyncLockContext, SyncBusyError
from siaps.validators import (
    validate_period,
    validate_team_type,
    validate_action_payload,
    validate_csv_filename,
    sanitize_csv_formula,
    ValidationError,
)
from siaps.ingestion import _validate_safe_url


class TestSecurityHeaders(unittest.TestCase):
    """Verifica cabeçalhos de segurança HTTP (OWASP ASVS / Diretrizes de Segurança)."""

    def setUp(self):
        self.client = app.test_client()

    def test_security_headers_present_on_response(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

        # Content-Security-Policy
        self.assertIn("Content-Security-Policy", resp.headers)
        csp = resp.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)

        # X-Content-Type-Options
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")

        # X-Frame-Options
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")

        # Referrer-Policy
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

        # Permissions-Policy
        self.assertIn("geolocation=()", resp.headers.get("Permissions-Policy", ""))


class TestInputValidators(unittest.TestCase):
    """Verifica validação estrita de todas as entradas do usuário."""

    def test_validate_period_valid(self):
        self.assertEqual(validate_period("2026Q1"), "2026Q1")
        self.assertEqual(validate_period("2025Q3"), "2025Q3")

    def test_validate_period_invalid(self):
        invalid_cases = ["", "2026", "2026Q5", "2026Q0", "2026-Q1", "'; DROP TABLE teams;--", "Q12026"]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    validate_period(case)

    def test_validate_team_type_valid(self):
        self.assertEqual(validate_team_type("eSF"), "eSF")
        self.assertEqual(validate_team_type("eSB"), "eSB")
        self.assertEqual(validate_team_type("eMulti"), "eMulti")

    def test_validate_team_type_invalid_and_excluded(self):
        # Excluídos da NT 8/2026 ou tipos inválidos
        invalid_cases = ["eAPP", "eCR", "eSFR", "TODOS", "ADMIN", "123", ""]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    validate_team_type(case)

    def test_validate_csv_filename_safe(self):
        valid = "Relatorio_Publico_Classificacao_Geral_dos_Componentes.csv"
        self.assertEqual(validate_csv_filename(valid), valid)

    def test_validate_csv_filename_rejection(self):
        malicious = [
            "../../etc/passwd",
            "../app.py",
            "Relatorio_Publico.exe",
            "Relatorio_Publico.csv;rm -rf /",
            "unauthorized_file.csv",
        ]
        for name in malicious:
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    validate_csv_filename(name)

    def test_sanitize_csv_formula(self):
        self.assertEqual(sanitize_csv_formula("=SUM(A1:A10)"), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_csv_formula("+CMD('calc')"), "'+CMD('calc')")
        self.assertEqual(sanitize_csv_formula("-10+5"), "'-10+5")
        self.assertEqual(sanitize_csv_formula("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(sanitize_csv_formula("Texto Normal"), "Texto Normal")
        self.assertEqual(sanitize_csv_formula(1234), "1234")

    def test_validate_action_payload_valid(self):
        payload = {
            "title": "Capacitação em pré-natal odontológico",
            "description": "Oficina com a equipe de saúde bucal e enfermagem para busca ativa",
            "responsible": "Coordenação da Atenção Primária",
            "deadline": "2026-11-30",
            "team_ine": "0000123456",
            "indicator_key": "PROP_GESTANTES_ODONTO",
            "priority": "alta",
        }
        cleaned = validate_action_payload(payload)
        self.assertEqual(cleaned["title"], payload["title"])
        self.assertEqual(cleaned["priority"], "alta")

    def test_validate_action_payload_rejects_cpf_cns_lgpd(self):
        # Proteção LGPD: rejeita CPF ou CNS em campos livres
        payload_with_cpf = {
            "title": "Acompanhar paciente CPF 123.456.789-00",
            "responsible": "Coordenação",
        }
        with self.assertRaises(ValidationError) as ctx:
            validate_action_payload(payload_with_cpf)
        self.assertIn("cpf", str(ctx.exception).lower())

        payload_with_cns = {
            "title": "Acompanhamento pré-natal",
            "description": "Cartão SUS CNS 700000000000001",
            "responsible": "Coordenação",
        }
        with self.assertRaises(ValidationError) as ctx:
            validate_action_payload(payload_with_cns)
        self.assertIn("sus", str(ctx.exception).lower())

    def test_validate_action_payload_length_limits(self):
        payload_long_title = {
            "title": "A" * 300,
            "responsible": "Coordenação",
        }
        with self.assertRaises(ValidationError):
            validate_action_payload(payload_long_title)


class TestSSRFProtection(unittest.TestCase):
    """Verifica restrição estrita de destinos de rede na coleta pública."""

    def test_safe_url_allowed(self):
        allowed = "https://apisiaps.saude.gov.br/api/public/componente/indicador-quadrimestre/filtro"
        self.assertEqual(_validate_safe_url(allowed), allowed)

    def test_unauthorized_urls_blocked(self):
        blocked = [
            "http://apisiaps.saude.gov.br/api",  # Rejeita HTTP não seguro
            "https://evil.com/api",
            "https://localhost:8080/internal",
            "file:///etc/passwd",
            "ftp://files.saude.gov.br",
        ]
        for url in blocked:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    _validate_safe_url(url)


class TestConcurrencyLock(unittest.TestCase):
    """Verifica impedimento de execuções simultâneas de sincronização."""

    def test_sync_lock_mutex(self):
        with SyncLockContext():
            # Segunda tentativa concorrente deve falhar imediatamente com SyncBusyError
            with self.assertRaises(SyncBusyError):
                with SyncLockContext():
                    pass

        # Após liberar o contexto, deve ser possível adquirir o lock novamente
        with SyncLockContext():
            pass


class TestProportionalAuthorization(unittest.TestCase):
    """Verifica controle de autorização proporcional com chave administrativa."""

    def setUp(self):
        self.client = app.test_client()

    def test_sync_endpoint_open_when_no_key_configured(self):
        with patch.dict(os.environ, {"SIAPS_ADMIN_KEY": ""}):
            with patch("app.sync_siaps_data") as mock_sync:
                mock_sync.return_value = {"status": "success", "unchanged": 4}
                resp = self.client.post("/api/sync")
                self.assertIn(resp.status_code, [200, 409])

    def test_sync_endpoint_protected_when_admin_key_set(self):
        with patch.dict(os.environ, {"SIAPS_ADMIN_KEY": "pacuja-admin-secret-2026"}):
            # Sem cabeçalho -> 401 Unauthorized
            resp_no_header = self.client.post("/api/sync")
            self.assertEqual(resp_no_header.status_code, 401)

            # Com chave incorreta -> 401 Unauthorized
            resp_wrong = self.client.post("/api/sync", headers={"X-Admin-Key": "wrong-secret"})
            self.assertEqual(resp_wrong.status_code, 401)

            # Com chave correta -> Autorizado
            with patch("app.sync_siaps_data") as mock_sync:
                mock_sync.return_value = {"status": "success", "unchanged": 4}
                resp_correct = self.client.post("/api/sync", headers={"X-Admin-Key": "pacuja-admin-secret-2026"})
                self.assertEqual(resp_correct.status_code, 200)


class TestBackupAndExport(unittest.TestCase):
    """Verifica funcionalidade de exportação e integridade de backup."""

    def setUp(self):
        self.client = app.test_client()

    def test_backup_export_schema_and_integrity(self):
        resp = self.client.get("/api/export/backup")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("application", data)
        self.assertIn("municipality", data)
        self.assertEqual(data["municipality"], "Pacujá")
        self.assertEqual(data["ibge"], "230990")
        self.assertIn("sha256_integrity", data)
        self.assertIn("teams", data)
        self.assertIn("component_summaries", data)


if __name__ == "__main__":
    unittest.main()
