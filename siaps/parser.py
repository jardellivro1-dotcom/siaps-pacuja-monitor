from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any


class ParseValidationError(Exception):
    """Raised when CSV validation fails due to wrong territory, corrupted header, or missing columns."""
    pass


def parse_siaps_csv(content: str) -> dict[str, Any]:
    """
    Parses a Siaps public CSV report.
    Validates institutional header, territory (CE / Pacujá - 230990), header columns, and data rows.
    """
    lines = [line.strip("\r\n") for line in content.splitlines()]
    if not lines:
        raise ParseValidationError("Arquivo CSV vazio.")

    # Validate institutional header
    if not any("Ministério da Saúde" in line or "Ministerio da Saude" in line for line in lines[:5]):
        raise ParseValidationError("Cabeçalho institucional do Ministério da Saúde / Siaps não encontrado.")

    # Validate territory
    demographic_lines = lines[:15]
    has_ce = any("UF: CE" in l or "Estado: CE" in l for l in demographic_lines)
    has_pacuja = any("230990" in l or "PACUJ" in l.upper() for l in demographic_lines)
    if not (has_ce and has_pacuja):
        raise ParseValidationError("Arquivo rejeitado: não pertence ao município de Pacujá, Ceará (230990).")

    # Detect report type by finding the table header row
    header_idx = -1
    report_type = None

    for i, line in enumerate(lines):
        if line.startswith("Quadrimestre/Ano"):
            header_idx = i
            if "Classificação por tipo de equipe" in line or "Dimensão por tipo de equipe" in line:
                report_type = "cvat_dimensao"
            elif "Indicador por tipo de equipe" in line:
                report_type = "qualidade_indicador"
            elif "Classificação Final OTIMO" in line or "Classificacao Final OTIMO" in line:
                report_type = "qualidade_final"
            elif "Classificação Final" in line or "Classificacao Final" in line:
                report_type = "geral_componentes"
            break

    if header_idx == -1 or report_type is None:
        raise ParseValidationError("Linha de cabeçalho da tabela de dados não encontrada ou tipo desconhecido.")

    # Parse CSV table starting from header_idx
    csv_text = "\n".join(lines[header_idx:])
    reader = csv.reader(io.StringIO(csv_text), delimiter=";")
    rows = list(reader)

    header_cols = [c.strip().strip('"').rstrip("\t") for c in rows[0]]
    data_rows = []

    for r in rows[1:]:
        # Stop if we hit footer or dictionary
        if not r or not r[0] or "Fonte:" in r[0] or "Legenda" in r[0] or "Mais informacoes:" in r[0]:
            break
        cleaned_cells = [cell.strip().strip('"').rstrip("\t") for cell in r]
        # Ignore empty row
        if not any(cleaned_cells):
            continue
        data_rows.append(cleaned_cells)

    return {
        "report_type": report_type,
        "header": header_cols,
        "rows": data_rows,
        "total_rows": len(data_rows),
    }


def normalize_int(val: Any) -> int | None:
    if val is None or val == "" or str(val).strip() in ("-", "—"):
        return None
    try:
        return int(float(str(val).replace(",", ".")))
    except (ValueError, TypeError):
        return None


def normalize_float(val: Any) -> float | None:
    if val is None or val == "" or str(val).strip() in ("-", "—"):
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None
