"""
Módulo de Autenticação, Autorização e Auditoria (RBAC) para o Monitor APS Pacujá.
Conforme OWASP ASVS v4.0.3 e padrões de governança do SUS.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from siaps.models import get_connection, init_db

# Constantes de Segurança
SESSION_COOKIE_NAME = "siaps_session"
SESSION_DURATION_HOURS = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

ALLOWED_ROLES = {"admin", "coordenador_aps", "equipe_saude", "leitor"}


class AuthError(Exception):
    """Exceção levantada em falhas de autenticação e autorização."""
    pass


def log_audit(
    db_path: Path | None,
    action: str,
    resource: str | None = None,
    details: str | None = None,
    user_id: int | None = None,
    username: str = "anonimo",
    ip_address: str | None = None,
    status: str = "success",
) -> None:
    """Registra evento na trilha de auditoria imutável."""
    try:
        conn = get_connection(db_path)
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute(
                """
                INSERT INTO audit_log (user_id, username, action, resource, details, ip_address, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, action, resource, details, ip_address, status, now),
            )
        conn.close()
    except Exception:
        pass


def create_user(
    username: str,
    password: str,
    full_name: str,
    role: str = "leitor",
    email: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Cria um novo usuário com senha criptografada via PBKDF2/SHA256."""
    username_clean = username.strip().lower()
    if len(username_clean) < 3 or len(username_clean) > 30:
        raise AuthError("O nome de usuário deve ter entre 3 e 30 caracteres.")
    if len(password) < 8:
        raise AuthError("A senha deve conter no mínimo 8 caracteres.")
    if role not in ALLOWED_ROLES:
        raise AuthError(f"Papel '{role}' inválido. Permitidos: {', '.join(sorted(ALLOWED_ROLES))}.")

    init_db(db_path)
    conn = get_connection(db_path)
    pwd_hash = generate_password_hash(password, method="scrypt")
    now = datetime.now(timezone.utc).isoformat()

    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, email, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username_clean, pwd_hash, full_name.strip(), email, role, now),
            )
            user_id = cur.lastrowid
        conn.close()
        return {"id": user_id, "username": username_clean, "role": role}
    except Exception as exc:
        conn.close()
        raise AuthError(f"Usuário '{username_clean}' já existe ou dados inválidos.") from exc


def authenticate_user(
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Autentica o usuário com proteção contra ataques de força bruta."""
    username_clean = username.strip().lower()
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    user = conn.execute("SELECT * FROM users WHERE username = ?", (username_clean,)).fetchone()

    if not user:
        conn.close()
        log_audit(db_path, "login_failed", "auth", f"Usuário inexistente: {username_clean}", username=username_clean, ip_address=ip_address, status="denied")
        raise AuthError("Credenciais inválidas.")

    # Verifica bloqueio por tentativas excessivas
    if user["locked_until"]:
        try:
            locked_dt = datetime.fromisoformat(user["locked_until"])
            if now < locked_dt:
                conn.close()
                minutos_restantes = max(1, int((locked_dt - now).total_seconds() / 60))
                log_audit(db_path, "login_blocked", "auth", f"Conta bloqueada temporariamente", user_id=user["id"], username=username_clean, ip_address=ip_address, status="blocked")
                raise AuthError(f"Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em {minutos_restantes} minuto(s).")
        except ValueError:
            pass

    if not user["is_active"]:
        conn.close()
        raise AuthError("Esta conta de usuário está desativada pela administração.")

    if not check_password_hash(user["password_hash"], password):
        # Incrementa contador de falhas
        falhas = user["failed_login_attempts"] + 1
        lock_until = None
        if falhas >= MAX_FAILED_ATTEMPTS:
            lock_until = (now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
            falhas = 0

        with conn:
            conn.execute(
                "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?",
                (falhas, lock_until, user["id"]),
            )
        conn.close()

        log_audit(db_path, "login_failed", "auth", f"Senha incorreta (tentativa {falhas})", user_id=user["id"], username=username_clean, ip_address=ip_address, status="denied")
        raise AuthError("Credenciais inválidas.")

    # Sucesso: zera falhas e atualiza último login
    session_token = secrets.token_hex(32)
    expires_at = (now + timedelta(hours=SESSION_DURATION_HOURS)).isoformat()

    with conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login = ? WHERE id = ?",
            (now_iso, user["id"]),
        )
        conn.execute(
            """
            INSERT INTO user_sessions (session_token, user_id, ip_address, user_agent, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_token, user["id"], ip_address, (user_agent or "")[:200], now_iso, expires_at),
        )
    conn.close()

    log_audit(db_path, "login_success", "auth", f"Login efetuado com papel {user['role']}", user_id=user["id"], username=username_clean, ip_address=ip_address)

    return {
        "session_token": session_token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
        "expires_at": expires_at,
    }


def get_current_user_from_request(db_path: Path | None = None) -> dict[str, Any] | None:
    """Extrai e valida a sessão do usuário a partir de cookies ou header Authorization."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    conn = get_connection(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    session = conn.execute(
        """
        SELECT s.session_token, s.expires_at, u.id, u.username, u.full_name, u.role, u.is_active
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = ? AND s.expires_at > ? AND u.is_active = 1
        """,
        (token, now_iso),
    ).fetchone()
    conn.close()

    if session:
        return {
            "id": session["id"],
            "username": session["username"],
            "full_name": session["full_name"],
            "role": session["role"],
            "token": token,
        }
    return None


def destroy_session(token: str, db_path: Path | None = None) -> None:
    """Encerra a sessão revogando o token no banco."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
    conn.close()


def login_required(f: Callable) -> Callable:
    """Decorador que exige autenticação ativa para acessar a rota."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        db_path = getattr(g, "db_path", None)
        user = get_current_user_from_request(db_path)
        if not user:
            if request.path.startswith("/api/"):
                return jsonify(error="Autenticação obrigatória.", message="Faça login para realizar esta operação."), 401
            from flask import redirect, url_for
            return redirect(url_for("login_view", next=request.path))
        g.user = user
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles: str) -> Callable:
    """Decorador que restringe a rota a usuários com determinados papéis (RBAC)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            db_path = getattr(g, "db_path", None)
            user = get_current_user_from_request(db_path)
            if not user:
                return jsonify(error="Não autenticado.", message="Efetue login para continuar."), 401
            if user["role"] not in allowed_roles and user["role"] != "admin":
                log_audit(db_path, "access_denied", request.path, f"Papel {user['role']} sem permissão (requer {allowed_roles})", user_id=user["id"], username=user["username"], status="forbidden")
                return jsonify(error="Acesso negado.", message="Seu perfil de acesso não possui permissão para esta ação."), 403
            g.user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def ensure_initial_users(db_path: Path | None = None) -> None:
    """Garante a existência dos perfis de acesso institucionais mínimos para homologação municipal."""
    init_db(db_path)
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    conn.close()

    if count == 0:
        admin_pass = os.environ.get("SIAPS_ADMIN_PASSWORD", "Pacuja@APS2026")
        coord_pass = os.environ.get("SIAPS_COORD_PASSWORD", "Coord@Pacuja2026")
        equipe_pass = os.environ.get("SIAPS_EQUIPE_PASSWORD", "Equipe@Pacuja2026")

        create_user("admin", admin_pass, "Administrador da Secretaria de Saúde", role="admin", db_path=db_path)
        create_user("coordenacao_aps", coord_pass, "Coordenação da Atenção Primária", role="coordenador_aps", db_path=db_path)
        create_user("equipe_pacuja", equipe_pass, "Equipes de Saúde de Pacujá", role="equipe_saude", db_path=db_path)
