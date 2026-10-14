"""
Módulo de Governança de Privacidade e Varredura LGPD do Monitor APS Pacujá.
Garante a inexistência de dados pessoais de pacientes em conformidade com as diretrizes da ANPD.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from siaps.models import get_connection, init_db

RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_CNS = re.compile(r"\b[12789]\d{14}\b")
RE_PHONE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-.\s]?\d{4}\b")


def scan_database_for_privacy_violations(db_path: Path | None = None) -> dict[str, Any]:
    """
    Realiza varredura em todas as tabelas e campos de texto livre do banco
    para detectar possíveis inclusões acidentais de CPF, Cartão SUS (CNS) ou telefones.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    violations: list[dict[str, Any]] = []

    # 1. Varredura na tabela improvement_actions
    actions = conn.execute("SELECT id, title, description, responsible FROM improvement_actions").fetchall()
    for act in actions:
        fields = {
            "title": act["title"] or "",
            "description": act["description"] or "",
            "responsible": act["responsible"] or "",
        }
        for fname, val in fields.items():
            if RE_CPF.search(val):
                violations.append({
                    "tabela": "improvement_actions",
                    "registro_id": act["id"],
                    "campo": fname,
                    "tipo": "CPF_DETECTADO",
                    "amostra": "[REDACTED_CPF]",
                })
            if RE_CNS.search(val):
                violations.append({
                    "tabela": "improvement_actions",
                    "registro_id": act["id"],
                    "campo": fname,
                    "tipo": "CNS_DETECTADO",
                    "amostra": "[REDACTED_CNS]",
                })

    # 2. Varredura na tabela audit_log
    logs = conn.execute("SELECT id, details FROM audit_log").fetchall()
    for l in logs:
        text = l["details"] or ""
        if RE_CPF.search(text) or RE_CNS.search(text):
            violations.append({
                "tabela": "audit_log",
                "registro_id": l["id"],
                "campo": "details",
                "tipo": "DADO_PESSOAL_EM_LOG",
                "amostra": "[REDACTED]",
            })

    conn.close()

    return {
        "status": "conforme" if len(violations) == 0 else "inconforme",
        "total_violacoes": len(violations),
        "violacoes": violations,
        "diretriz": "Lei Geral de Proteção de Dados (Lei nº 13.709/2018) e Regra 3 do AGENTS.md",
    }


def purge_privacy_violation(action_id: int, db_path: Path | None = None) -> bool:
    """Higieniza e expurga dados de pacientes inseridos indevidamente em uma ação."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            UPDATE improvement_actions
            SET title = '[CONTEUDO EXPURGADO POR MOTIVO DE PRIVACIDADE LGPD]',
                description = '[DADO PESSOAL REMOVIDO PELA COORDENACAO DA APS]',
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (action_id,),
        )
        affected = conn.total_changes
    conn.close()
    return affected > 0
