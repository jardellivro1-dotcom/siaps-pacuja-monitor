import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app
from scripts.backup_external import create_external_backup
from siaps.alerts import send_external_alert
from siaps.auth import (
    AuthError,
    SESSION_COOKIE_NAME,
    authenticate_user,
    create_user,
    destroy_session,
    ensure_initial_users,
    log_audit,
)
from siaps.models import get_connection, init_db
from siaps.privacy import purge_privacy_violation, scan_database_for_privacy_violations


class TestAuthAndRBAC(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_auth.db"
        self.raw_dir = Path(self.temp_dir.name) / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        init_db(self.db_path)

        self.app = create_app({
            "TESTING": True,
            "DB_PATH": self.db_path,
            "RAW_DATA_DIR": self.raw_dir,
            "SECRET_KEY": "test-secret-key-pacuja",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_initial_users_creates_default_accounts(self):
        ensure_initial_users(self.db_path)
        conn = get_connection(self.db_path)
        users = [r["username"] for r in conn.execute("SELECT username FROM users").fetchall()]
        conn.close()

        self.assertIn("admin", users)
        self.assertIn("coordenacao_aps", users)
        self.assertIn("equipe_pacuja", users)

    def test_create_user_validations(self):
        # Invalid role
        with self.assertRaises(AuthError):
            create_user("gestor", "SenhaSegura123", "Gestor", role="papel_invalido", db_path=self.db_path)

        # Password too short (< 8 chars)
        with self.assertRaises(AuthError):
            create_user("gestor", "curta", "Gestor", role="coordenador_aps", db_path=self.db_path)

        # Valid creation
        res = create_user("enfermeiro_psf", "SenhaForte2026", "Enfermeiro PSF 1", role="equipe_saude", db_path=self.db_path)
        self.assertEqual(res["username"], "enfermeiro_psf")
        self.assertEqual(res["role"], "equipe_saude")

        # Duplicate username error
        with self.assertRaises(AuthError):
            create_user("enfermeiro_psf", "OutraSenha2026", "Enfermeiro PSF 1", role="equipe_saude", db_path=self.db_path)

    def test_authenticate_and_session(self):
        create_user("dra_maria", "MedicaPacuja2026", "Dra. Maria", role="equipe_saude", db_path=self.db_path)

        # Wrong password
        with self.assertRaises(AuthError) as ctx:
            authenticate_user("dra_maria", "SenhaErrada", db_path=self.db_path)
        self.assertIn("Credenciais inválidas", str(ctx.exception))

        # Correct password
        auth_res = authenticate_user("dra_maria", "MedicaPacuja2026", ip_address="127.0.0.1", db_path=self.db_path)
        self.assertIn("session_token", auth_res)
        self.assertEqual(auth_res["user"]["username"], "dra_maria")
        self.assertEqual(auth_res["user"]["role"], "equipe_saude")

        # Invalidate session
        destroy_session(auth_res["session_token"], db_path=self.db_path)
        conn = get_connection(self.db_path)
        session_row = conn.execute("SELECT * FROM user_sessions WHERE session_token = ?", (auth_res["session_token"],)).fetchone()
        conn.close()
        self.assertIsNone(session_row)

    def test_brute_force_lockout_after_5_failed_attempts(self):
        create_user("vitima_ataque", "SenhaSuperSegura2026", "Usuario Teste", role="leitor", db_path=self.db_path)

        # 4 consecutive failures
        for _ in range(4):
            with self.assertRaises(AuthError):
                authenticate_user("vitima_ataque", "senha_incorreta", db_path=self.db_path)

        # 5th failure triggers lockout
        with self.assertRaises(AuthError):
            authenticate_user("vitima_ataque", "senha_incorreta", db_path=self.db_path)

        # Even with correct password, account must remain locked
        with self.assertRaises(AuthError) as locked_ctx:
            authenticate_user("vitima_ataque", "SenhaSuperSegura2026", db_path=self.db_path)
        self.assertIn("bloqueada", str(locked_ctx.exception).lower())

    def test_api_auth_login_logout_me_endpoints(self):
        create_user("coordenador1", "CoordPacuja2026", "Coordenador APS", role="coordenador_aps", db_path=self.db_path)

        # Check /api/auth/me when unauthenticated
        res_me_unauth = self.client.get("/api/auth/me")
        self.assertEqual(res_me_unauth.status_code, 200)
        self.assertFalse(res_me_unauth.json["authenticated"])

        # Login endpoint with valid credentials
        res_login = self.client.post("/api/auth/login", json={
            "username": "coordenador1",
            "password": "CoordPacuja2026"
        })
        self.assertEqual(res_login.status_code, 200)
        self.assertEqual(res_login.json["status"], "authenticated")
        token = res_login.json["token"]
        self.assertTrue(len(token) > 20)

        # Check /api/auth/me when authenticated via cookie
        res_me_auth = self.client.get("/api/auth/me")
        self.assertEqual(res_me_auth.status_code, 200)
        self.assertTrue(res_me_auth.json["authenticated"])
        self.assertEqual(res_me_auth.json["user"]["username"], "coordenador1")
        self.assertEqual(res_me_auth.json["user"]["role"], "coordenador_aps")

        # Logout endpoint
        res_logout = self.client.post("/api/auth/logout")
        self.assertEqual(res_logout.status_code, 200)

        # Check /api/auth/me after logout
        res_me_after = self.client.get("/api/auth/me")
        self.assertFalse(res_me_after.json["authenticated"])

    def test_rbac_restriction_when_auth_enforced(self):
        create_user("leitor_cidadao", "CidadaoPacuja2026", "Cidadão Leitor", role="leitor", db_path=self.db_path)
        create_user("admin_geral", "AdminPacuja2026", "Admin Geral", role="admin", db_path=self.db_path)

        # Simulate strict auth mode
        os.environ["SIAPS_REQUIRE_AUTH"] = "1"
        try:
            # 1. Unauthenticated write must return 401
            res = self.client.post("/api/actions", json={"title": "Teste"})
            self.assertEqual(res.status_code, 401)

            # 2. Login as leitor
            self.client.post("/api/auth/login", json={
                "username": "leitor_cidadao",
                "password": "CidadaoPacuja2026"
            })

            # Leitor trying to create action must return 403 Forbidden
            res_forbidden = self.client.post("/api/actions", json={
                "title": "Ação Proibida",
                "description": "Tentativa de escrita por leitor",
                "team_type": "eSF",
                "indicator_code": "C1",
                "indicator_name": "Pré-Natal",
                "responsible": "Leitor",
                "deadline": "2026-12-31",
                "status": "pendente",
            })
            self.assertEqual(res_forbidden.status_code, 403)

            # 3. Login as admin
            self.client.post("/api/auth/login", json={
                "username": "admin_geral",
                "password": "AdminPacuja2026"
            })

            # Admin allowed
            res_allowed = self.client.post("/api/actions", json={
                "title": "Ação Autorizada",
                "description": "Ação criada por administrador",
                "team_type": "eSF",
                "indicator_code": "C1",
                "indicator_name": "Pré-Natal",
                "responsible": "Coordenação",
                "deadline": "2026-12-31",
                "status": "pendente",
            })
            self.assertEqual(res_allowed.status_code, 201)

        finally:
            os.environ.pop("SIAPS_REQUIRE_AUTH", None)


class TestPrivacyAndOperationalResilience(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ops.db"
        self.raw_dir = Path(self.temp_dir.name) / "raw"
        self.backup_dir = Path(self.temp_dir.name) / "backups"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_and_purge_privacy_violations(self):
        # Insert clean action
        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO improvement_actions (title, description, team_type, indicator_code, indicator_name, responsible, deadline, status, created_at, updated_at)
                VALUES ('Ação Normal', 'Sem dados pessoais', 'eSF', 'C1', 'Pré-Natal', 'Equipe', '2026-12-31', 'pendente', '2026-01-01', '2026-01-01')
                """
            )
        conn.close()

        scan_res = scan_database_for_privacy_violations(self.db_path)
        self.assertEqual(scan_res["total_violacoes"], 0)
        self.assertEqual(scan_res["status"], "conforme")

        # Inject CPF in violation of LGPD
        conn = get_connection(self.db_path)
        with conn:
            cur = conn.execute(
                """
                INSERT INTO improvement_actions (title, description, team_type, indicator_code, indicator_name, responsible, deadline, status, created_at, updated_at)
                VALUES ('Acompanhar paciente', 'Verificar o CPF 123.456.789-00 no posto', 'eSF', 'C2', 'Vacinação', 'Equipe', '2026-12-31', 'pendente', '2026-01-01', '2026-01-01')
                """
            )
            injected_action_id = cur.lastrowid
        conn.close()

        scan_res = scan_database_for_privacy_violations(self.db_path)
        self.assertEqual(scan_res["total_violacoes"], 1)
        self.assertEqual(scan_res["status"], "inconforme")
        self.assertEqual(scan_res["violacoes"][0]["tipo"], "CPF_DETECTADO")

        # Purge violation
        purge_res = purge_privacy_violation(
            action_id=injected_action_id,
            db_path=self.db_path,
        )
        self.assertTrue(purge_res)

        # Verify no violations remain
        remaining = scan_database_for_privacy_violations(self.db_path)
        self.assertEqual(remaining["total_violacoes"], 0)
        self.assertEqual(remaining["status"], "conforme")

    def test_external_alert_dispatcher(self):
        # Webhook without env var defaults to logger without error
        res = send_external_alert(
            level="info",
            title="Alerta de Teste",
            message="Mensagem simulada de monitoramento",
        )
        self.assertTrue(res)

    def test_hot_backup_generation_and_integrity(self):
        # Create dummy CSV in raw_dir
        (self.raw_dir / "indicadores_teste.csv").write_text("dummy csv data", encoding="utf-8")

        result = create_external_backup(
            dest_dir=self.backup_dir,
            db_path=self.db_path,
            raw_dir=self.raw_dir,
            retention_count=3,
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["archive"]).exists())
        self.assertTrue(len(result["sha256"]) == 64)


if __name__ == "__main__":
    unittest.main()
