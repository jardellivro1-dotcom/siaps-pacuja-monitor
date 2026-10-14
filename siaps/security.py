from __future__ import annotations

import os
import threading
from functools import wraps
from pathlib import Path
from flask import Request, Response, abort, jsonify, request


# Lock de concorrência em memória para impedir execuções simultâneas de sincronização
_SYNC_LOCK = threading.Lock()


class SyncBusyError(Exception):
    """Exceção levantada quando uma sincronização já está em andamento."""
    pass


class SyncLockContext:
    """Context manager não-bloqueante para garantir exclusividade da sincronização."""
    def __enter__(self):
        acquired = _SYNC_LOCK.acquire(blocking=False)
        if not acquired:
            raise SyncBusyError("Uma sincronização de dados já está em execução. Aguarde a conclusão da tarefa atual.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _SYNC_LOCK.release()


def apply_security_headers(response: Response) -> Response:
    """
    Aplica cabeçalhos de segurança recomendados pelo OWASP ASVS e melhores práticas do setor:
    - Prevenção de Clickjacking (X-Frame-Options)
    - Prevenção de MIME-Sniffing (X-Content-Type-Options)
    - Controle de Referência (Referrer-Policy)
    - Content Security Policy restritivo (CSP)
    - HSTS para forçar canais criptografados
    - Permissions-Policy para desativar APIs desnecessárias
    """
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    return response


def require_admin_if_configured(f):
    """
    Decorator que implementa autorização proporcional:
    Se a variável de ambiente SIAPS_ADMIN_KEY estiver definida,
    exige o cabeçalho 'X-Admin-Key' ou 'Authorization: Bearer <key>'.
    Se não estiver definida, a aplicação funciona em modo aberto para a rede local/intranet da gestão.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = os.environ.get("SIAPS_ADMIN_KEY")
        if admin_key:
            header_key = request.headers.get("X-Admin-Key")
            auth_header = request.headers.get("Authorization", "")
            bearer_key = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

            if header_key != admin_key and bearer_key != admin_key:
                return jsonify({
                    "error": "Acesso não autorizado.",
                    "message": "Operação restrita. Forneça a chave administrativa no cabeçalho 'X-Admin-Key'."
                }), 401

        return f(*args, **kwargs)
    return decorated_function
