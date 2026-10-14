from __future__ import annotations

from dataclasses import dataclass
from typing import Any


METODOLOGIA_INFO = {
    "documento": "Nota Técnica nº 8/2026-DEAPS/SAPS/MS",
    "publicacao": "02/10/2026",
    "revoga": "Nota Técnica nº 6/2025",
    "equipes_elegiveis": ["eSF", "eAP", "eSB", "eMulti"],
    "equipes_excluidas": ["eAPP", "eCR", "eSFR"],
}

# Conceitos por indicador para o Componente III
CONCEITO_VALORES = {
    "REGULAR": 0.25,
    "SUFICIENTE": 0.50,
    "BOM": 0.75,
    "OTIMO": 1.00,
    "ÓTIMO": 1.00,
}

# Indicadores e Pesos Oficiais por Tipo de Equipe (NT 8/2026)
INDICADORES_PESOS = {
    "eSF": {
        "C1": {"nome": "Mais acesso à APS", "peso": 1, "janela": "Últimos 30 dias", "coTipo": 110},
        "C2": {"nome": "Cuidado no desenvolvimento infantil", "peso": 2, "janela": "Últimos 24 meses", "coTipo": 108},
        "C3": {"nome": "Cuidado na gestação e puerpério", "peso": 2, "janela": "Últimos 12 meses", "coTipo": 107},
        "C4": {"nome": "Cuidado da pessoa com diabetes", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 105},
        "C5": {"nome": "Cuidado da pessoa com hipertensão", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 104},
        "C6": {"nome": "Cuidado da pessoa idosa", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 106},
        "C7": {"nome": "Cuidado da mulher na prevenção do câncer", "peso": 2, "janela": "Últimos 60 meses", "coTipo": 109},
    },
    "eAP": {
        "C1": {"nome": "Mais acesso à APS", "peso": 1, "janela": "Últimos 30 dias", "coTipo": 110},
        "C2": {"nome": "Cuidado no desenvolvimento infantil", "peso": 2, "janela": "Últimos 24 meses", "coTipo": 108},
        "C3": {"nome": "Cuidado na gestação e puerpério", "peso": 2, "janela": "Últimos 12 meses", "coTipo": 107},
        "C4": {"nome": "Cuidado da pessoa com diabetes", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 105},
        "C5": {"nome": "Cuidado da pessoa com hipertensão", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 104},
        "C6": {"nome": "Cuidado da pessoa idosa", "peso": 1, "janela": "Últimos 12 meses", "coTipo": 106},
        "C7": {"nome": "Cuidado da mulher na prevenção do câncer", "peso": 2, "janela": "Últimos 60 meses", "coTipo": 109},
    },
    "eSB": {
        "B1": {"nome": "Primeira consulta odontológica programada", "peso": 2, "janela": "Últimos 30 dias", "coTipo": 111},
        "B2": {"nome": "Tratamento odontológico concluído", "peso": 2, "janela": "Últimos 30 dias", "coTipo": 112},
        "B3": {"nome": "Taxa de exodontias", "peso": 2, "janela": "Últimos 30 dias", "coTipo": 113},
        "B4": {"nome": "Escovação supervisionada em faixa etária escolar", "peso": 1, "janela": "Últimos 30 dias", "coTipo": 114},
        "B5": {"nome": "Procedimentos odontológicos individuais preventivos", "peso": 2, "janela": "Últimos 30 dias", "coTipo": 115},
        "B6": {"nome": "Tratamento restaurador atraumático", "peso": 1, "janela": "Últimos 30 dias", "coTipo": 116},
    },
    "eMulti": {
        "M1": {"nome": "Média de atendimentos da eMulti por pessoa", "peso": 6, "janela": "Últimos 4 meses", "coTipo": 117},
        "M2": {"nome": "Ações interprofissionais da eMulti", "peso": 4, "janela": "Últimos 4 meses", "coTipo": 118},
    },
}


@dataclass
class ScoreResult:
    nota: float | None
    classificacao: str
    is_completo: bool
    motivo_incompleto: str | None
    detalhes: dict[str, Any]


def classificar_componente_2(nota: float | None) -> str:
    """
    Classificação do Componente II (CVAT) conforme NT 8/2026:
    - Ótimo: > 8,5
    - Bom: >= 7,0 e <= 8,5
    - Suficiente: >= 5,0 e < 7,0
    - Regular: < 5,0
    """
    if nota is None:
        return "Indisponível"
    if nota > 8.5:
        return "Ótimo"
    if nota >= 7.0:
        return "Bom"
    if nota >= 5.0:
        return "Suficiente"
    return "Regular"


def classificar_componente_3(nota: float | None) -> str:
    """
    Classificação da nota final do Componente III (Qualidade) conforme NT 8/2026:
    - Ótimo: > 7,5
    - Bom: >= 5,0 e <= 7,5
    - Suficiente: > 2,5 e < 5,0
    - Regular: <= 2,5
    """
    if nota is None:
        return "Indisponível"
    if nota > 7.5:
        return "Ótimo"
    if nota >= 5.0:
        return "Bom"
    if nota > 2.5:
        return "Suficiente"
    return "Regular"


def calcular_nota_componente_3(
    team_type: str,
    indicadores_conceitos: dict[str, str | None],
) -> ScoreResult:
    """
    Calcula a nota final do Componente III ponderada pelos pesos oficiais da NT 8/2026.
    Retorna ScoreResult. Se faltar algum indicador obrigatório ou for tipo não elegível,
    marca is_completo=False com explicação.
    """
    if team_type in METODOLOGIA_INFO["equipes_excluidas"]:
        return ScoreResult(
            nota=None,
            classificacao="Não aplicável",
            is_completo=False,
            motivo_incompleto=f"A Nota Técnica nº 8/2026 não se aplica a equipes do tipo {team_type}.",
            detalhes={},
        )

    tabela_pesos = INDICADORES_PESOS.get(team_type)
    if not tabela_pesos:
        return ScoreResult(
            nota=None,
            classificacao="Não aplicável",
            is_completo=False,
            motivo_incompleto=f"Tipo de equipe {team_type} não possui tabela de indicadores na NT 8/2026.",
            detalhes={},
        )

    pontos_ponderados = 0.0
    peso_total = 0
    pesos_presentes = 0
    detalhes: dict[str, Any] = {}
    faltantes: list[str] = []

    for codigo, meta in tabela_pesos.items():
        peso = meta["peso"]
        peso_total += peso
        conceito = indicadores_conceitos.get(codigo)
        if conceito is None:
            faltantes.append(f"{codigo} ({meta['nome']})")
            detalhes[codigo] = {"peso": peso, "conceito": None, "valor": None, "pontos": None}
            continue

        conceito_norm = conceito.strip().upper()
        # mapeia com acento ou sem acento
        if conceito_norm in ("ÓTIMO", "OTIMO"):
            val = 1.00
        elif conceito_norm == "BOM":
            val = 0.75
        elif conceito_norm == "SUFICIENTE":
            val = 0.50
        elif conceito_norm == "REGULAR":
            val = 0.25
        else:
            faltantes.append(f"{codigo} (Conceito desconhecido: '{conceito}')")
            detalhes[codigo] = {"peso": peso, "conceito": conceito, "valor": None, "pontos": None}
            continue

        pts = val * peso
        pontos_ponderados += pts
        pesos_presentes += peso
        detalhes[codigo] = {
            "nome": meta["nome"],
            "peso": peso,
            "conceito": conceito,
            "valor": val,
            "pontos": pts,
        }

    if faltantes or pesos_presentes < peso_total:
        return ScoreResult(
            nota=round(pontos_ponderados, 2) if pesos_presentes > 0 else None,
            classificacao="Incompleto",
            is_completo=False,
            motivo_incompleto=f"Dados incompletos: faltam conceitos para {', '.join(faltantes)}.",
            detalhes=detalhes,
        )

    nota_final = round(pontos_ponderados, 2)
    classificacao = classificar_componente_3(nota_final)
    return ScoreResult(
        nota=nota_final,
        classificacao=classificacao,
        is_completo=True,
        motivo_incompleto=None,
        detalhes=detalhes,
    )
