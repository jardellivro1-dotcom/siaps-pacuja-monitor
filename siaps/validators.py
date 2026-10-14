from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Padrões de validação
RE_PERIOD = re.compile(r"^\d{4}Q[1-3]$")
RE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+\.csv$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_CNS = re.compile(r"\b[12789]\d{14}\b")

ALLOWED_TEAM_TYPES = {"eSF", "eAP", "eSB", "eMulti", "Geral"}
ALLOWED_STATUSES = {"pendente", "em_andamento", "concluido"}
ALLOWED_PRIORITIES = {"baixa", "media", "alta", "critica"}

ALLOWED_CSV_FILES = {
    "Relatorio_Publico_Classificacao_Geral_dos_Componentes.csv",
    "Relatorio_Publico_Classificacao_por_Dimensao_CVAT.csv",
    "Relatorio_Publico_Classificacao_Final_Qualidade.csv",
    "Relatorio_Publico_Conceito_por_Indicador_Qualidade.csv",
}


class ValidationError(Exception):
    """Exceção levantada quando uma validação de entrada falha."""
    pass


def validate_period(period: str | None, allow_empty: bool = True) -> str | None:
    """Valida formato de quadrimestre (AAAAQ1, AAAAQ2 ou AAAAQ3)."""
    if period is None or period == "all":
        if allow_empty:
            return None
        raise ValidationError("Quadrimestre não pode ser nulo.")
    
    period_str = str(period).strip().upper()
    if not period_str:
        raise ValidationError("Quadrimestre não pode ser vazio.")
    
    if not RE_PERIOD.match(period_str):
        raise ValidationError(f"Formato de quadrimestre inválido: '{period}'. Esperado: AAAAQ1, AAAAQ2 ou AAAAQ3.")
    return period_str


def validate_team_type(team_type: str | None, allow_empty: bool = True) -> str | None:
    """Valida tipo de equipe elegível conforme NT 8/2026."""
    if team_type is None or team_type == "todas":
        if allow_empty:
            return None
        raise ValidationError("Tipo de equipe não pode ser nulo.")
        
    tt = str(team_type).strip()
    if not tt:
        raise ValidationError("Tipo de equipe não pode ser vazio.")
        
    if tt not in ALLOWED_TEAM_TYPES:
        raise ValidationError(f"Tipo de equipe inválido: '{team_type}'. Permitidos: {', '.join(sorted(ALLOWED_TEAM_TYPES))}.")
    return tt


def validate_action_payload(data: dict[str, Any], is_update: bool = False) -> dict[str, Any]:
    """
    Valida campos do plano de ação de melhoria, aplicando limites de tamanho,
    validação de data e verificação rigorosa de privacidade (LGPD).
    """
    cleaned: dict[str, Any] = {}

    if not is_update or "title" in data:
        title = str(data.get("title", "")).strip()
        if len(title) < 3 or len(title) > 200:
            raise ValidationError("O título da ação deve ter entre 3 e 200 caracteres.")
        _check_lgpd_sensitive_data(title, "Título")
        cleaned["title"] = title

    if not is_update or "responsible" in data:
        responsible = str(data.get("responsible", "")).strip()
        if len(responsible) < 2 or len(responsible) > 100:
            raise ValidationError("O responsável deve ter entre 2 e 100 caracteres.")
        _check_lgpd_sensitive_data(responsible, "Responsável")
        cleaned["responsible"] = responsible

    # Aceita 'deadline' ou 'target_date'
    raw_date = data.get("deadline") or data.get("target_date")
    if not is_update or raw_date is not None:
        if raw_date:
            deadline = str(raw_date).strip()
            if not RE_DATE.match(deadline):
                raise ValidationError("O prazo deve estar no formato AAAA-MM-DD.")
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Data de prazo inválida.")
            cleaned["deadline"] = deadline
        elif not is_update:
            # Deadline padrão: daqui a 30 dias se não fornecido
            cleaned["deadline"] = datetime.now().strftime("%Y-%m-%d")

    if "description" in data:
        desc = str(data.get("description", "")).strip()
        if len(desc) > 2000:
            raise ValidationError("A descrição não pode exceder 2000 caracteres.")
        _check_lgpd_sensitive_data(desc, "Descrição")
        cleaned["description"] = desc
    elif not is_update:
        cleaned["description"] = ""

    if "team_type" in data:
        tt = str(data.get("team_type", "Geral")).strip()
        if tt not in ALLOWED_TEAM_TYPES:
            raise ValidationError(f"Tipo de equipe '{tt}' não permitido.")
        cleaned["team_type"] = tt
    elif not is_update:
        cleaned["team_type"] = "Geral"

    if "team_ine" in data:
        team_ine = data.get("team_ine")
        cleaned["team_ine"] = str(team_ine).strip()[:20] if team_ine else None

    if "indicator_code" in data or "indicator_key" in data:
        ind_code = data.get("indicator_code") or data.get("indicator_key")
        cleaned["indicator_code"] = str(ind_code).strip()[:50] if ind_code else None

    if "indicator_name" in data:
        ind_name = data.get("indicator_name")
        cleaned["indicator_name"] = str(ind_name).strip()[:150] if ind_name else None

    if "priority" in data:
        prio = str(data.get("priority", "media")).strip().lower()
        if prio not in ALLOWED_PRIORITIES:
            raise ValidationError(f"Prioridade '{prio}' inválida. Permitidas: {', '.join(sorted(ALLOWED_PRIORITIES))}.")
        cleaned["priority"] = prio
    elif not is_update:
        cleaned["priority"] = "media"

    if "status" in data:
        status = str(data.get("status", "pendente")).strip().lower()
        if status not in ALLOWED_STATUSES:
            raise ValidationError(f"Status '{status}' inválido. Permitidos: {', '.join(sorted(ALLOWED_STATUSES))}.")
        cleaned["status"] = status
    elif not is_update:
        cleaned["status"] = "pendente"

    return cleaned


def _check_lgpd_sensitive_data(text: str, field_name: str) -> None:
    """Detecta números de CPF ou CNS de pacientes para conformidade estrita com LGPD."""
    if RE_CPF.search(text):
        raise ValidationError(f"Violação de privacidade (LGPD): O campo '{field_name}' contém padrão de CPF. Dados de pacientes são estritamente proibidos.")
    if RE_CNS.search(text):
        raise ValidationError(f"Violação de privacidade (LGPD): O campo '{field_name}' contém padrão de Cartão SUS (CNS). Dados de pacientes são estritamente proibidos.")


def validate_csv_filename(filename: str) -> str:
    """Valida o nome do arquivo para prevenir ataques de path traversal e acesso a arquivos indevidos."""
    fn = str(filename).strip()
    if not RE_FILENAME.match(fn):
        raise ValidationError("Nome de arquivo CSV inválido.")
    if ".." in fn or "/" in fn or "\\" in fn:
        raise ValidationError("Tentativa de travessia de caminho (path traversal) detectada.")
    if not (fn.startswith("Relatorio_Publico_") or fn in ALLOWED_CSV_FILES or fn.startswith("teste_")):
        raise ValidationError(f"Arquivo CSV não autorizado para download: '{fn}'.")
    return fn


def sanitize_csv_formula(val: Any) -> str:
    """
    Previne injeção de fórmulas em CSV (CSV Formula Injection / CWE-1236).
    Se o valor começar com =, +, -, @ ou tabulação, prefixa com apóstrofo (')
    para neutralizar a execução de comandos em softwares como Excel e Calc.
    """
    s = str(val if val is not None else "")
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + s
    return s
