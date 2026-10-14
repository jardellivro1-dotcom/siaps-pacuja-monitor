"""
Módulo de Alertas Externos para Monitoramento do Siaps Pacujá.
Envia notificações em tempo real para Webhooks (Slack, Discord, Teams, e-mail/serviços de monitoramento).
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any


def send_external_alert(
    level: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> bool:
    """
    Envia notificação de alerta para o canal externo configurado via ALERT_WEBHOOK_URL.
    Retorna True se enviado com sucesso ou se nenhum webhook estiver configurado (modo silencioso).
    """
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        # Se nenhum webhook externo configurado, registra no log padrão e retorna
        print(f"[{datetime.now(timezone.utc).isoformat()}] [ALERTA-{level.upper()}] {title}: {message}")
        return True

    payload = {
        "sistema": "Monitor APS Pacujá",
        "municipio": "Pacujá - CE",
        "nivel": level.lower(),  # info, warning, error, critical
        "titulo": title,
        "mensagem": message,
        "detalhes": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Formatação compatível com Discord/Slack/Teams
    discord_slack_payload = {
        "text": f"🚨 *[{level.upper()}] Monitor APS Pacujá*: {title}\n{message}",
        "attachments": [
            {
                "color": "#dc2626" if level in ("error", "critical") else ("#f59e0b" if level == "warning" else "#10b981"),
                "title": title,
                "text": message,
                "fields": [{"title": k, "value": str(v), "short": True} for k, v in (details or {}).items()],
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ]
    }

    try:
        data_bytes = json.dumps(discord_slack_payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MonitorAPSPacuja-Alerter/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as exc:
        print(f"Falha ao despachar alerta externo para {webhook_url}: {exc}")
        return False


def alert_sync_failure(error_msg: str, trigger_type: str = "manual") -> None:
    send_external_alert(
        level="error",
        title="Falha na Sincronização do Siaps",
        message=f"A rotina de sincronização ({trigger_type}) falhou ao consultar o Siaps oficial.",
        details={"erro": error_msg, "gatilho": trigger_type},
    )


def alert_security_lockout(username: str, ip_address: str | None) -> None:
    send_external_alert(
        level="warning",
        title="Bloqueio por Tentativas Excessivas de Login",
        message=f"O usuário '{username}' foi temporariamente bloqueado após exceder o limite de tentativas de autenticação.",
        details={"usuario": username, "ip": ip_address or "desconhecido"},
    )


def alert_sync_success(period: str, changes: str) -> None:
    send_external_alert(
        level="info",
        title="Dados do Siaps Atualizados com Sucesso",
        message=f"Nova verificação concluída para Pacujá/CE: {changes}.",
        details={"periodo": period, "alteracoes": changes},
    )
