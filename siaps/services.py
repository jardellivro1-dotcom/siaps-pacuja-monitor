from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from siaps.calculations import (
    INDICADORES_PESOS,
    METODOLOGIA_INFO,
    calcular_nota_componente_3,
    classificar_componente_2,
    classificar_componente_3,
)
from siaps.models import get_connection, init_db


def get_system_status(db_path: Path | None = None, raw_dir: Path | None = None) -> dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)

    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    raw_files_count = len(list(raw_dir.glob("*.csv"))) if raw_dir.exists() else 0
    teams_count = conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
    last_sync = conn.execute(
        "SELECT timestamp, status, message FROM sync_history ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Get available periods
    periods_rows = conn.execute(
        "SELECT DISTINCT period FROM component_summaries ORDER BY period DESC"
    ).fetchall()
    periods = [r["period"] for r in periods_rows if r["period"]]

    if not periods:
        periods_raw = conn.execute(
            "SELECT DISTINCT nuQuadrimestre FROM (SELECT period AS nuQuadrimestre FROM cvat_dimension_results UNION SELECT period FROM quality_indicator_results)"
        ).fetchall()
        periods = [r["nuQuadrimestre"] for r in periods_raw if r["nuQuadrimestre"]]

    conn.close()

    status = "aguardando_dados" if raw_files_count == 0 else "dados_validados"
    msg = (
        "Nenhum CSV público foi importado ainda. Os cartões só serão preenchidos depois da validação do arquivo oficial."
        if raw_files_count == 0
        else f"{raw_files_count} arquivos públicos oficiais importados e auditados para Pacujá, CE."
    )

    return {
        "status": status,
        "municipality": "Pacujá",
        "state": "CE",
        "ibge": "230990",
        "reports_count": raw_files_count,
        "teams_count": teams_count,
        "available_periods": periods,
        "last_sync": dict(last_sync) if last_sync else None,
        "message": msg,
        "methodology": METODOLOGIA_INFO,
    }


def get_dashboard_summary(
    period: str | None = None,
    team_type: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)

    # Obter quadrimestres disponíveis
    periods_rows = conn.execute(
        """
        SELECT DISTINCT period FROM (
            SELECT period FROM component_summaries
            UNION
            SELECT period FROM cvat_dimension_results
            UNION
            SELECT period FROM quality_indicator_results
        ) ORDER BY period ASC
        """
    ).fetchall()
    available_periods = [r["period"] for r in periods_rows if r["period"]]

    if not available_periods:
        conn.close()
        return {
            "period": None,
            "available_periods": [],
            "kpis": {
                "component_2": {"score": None, "label": "—", "class": "empty", "desc": "Sem período validado"},
                "component_3": {"score": None, "label": "—", "class": "empty", "desc": "Sem período validado"},
                "teams_count": 0,
                "last_check": None,
            },
            "teams_distribution": {},
            "indicators": [],
            "attention_indicators": [],
            "time_series": {},
            "comparison": None,
        }

    # Se período não especificado ou inválido, seleciona o mais recente
    selected_period = period if period in available_periods else available_periods[-1]

    # Encontrar período anterior para cálculo de tendência
    selected_idx = available_periods.index(selected_period)
    previous_period = available_periods[selected_idx - 1] if selected_idx > 0 else None

    # Equipes cadastradas
    teams = conn.execute("SELECT co_equipe, no_equipe, sg_equipe FROM teams ORDER BY sg_equipe, no_equipe").fetchall()
    teams_list = [dict(t) for t in teams]

    # 1. Componente II (CVAT)
    cvat_rows = conn.execute(
        """
        SELECT sg_equipe, no_dimensao, qtd_otimo, qtd_bom, qtd_suficiente, qtd_regular
        FROM cvat_dimension_results
        WHERE period = ?
        """,
        (selected_period,),
    ).fetchall()

    cvat_dimensions = [dict(r) for r in cvat_rows]

    # 2. Componente III (Qualidade)
    comp3_query = "SELECT * FROM component_summaries WHERE period = ?"
    params: list[Any] = [selected_period]
    if team_type and team_type != "todas":
        comp3_query += " AND sg_equipe = ?"
        params.append(team_type)

    comp3_rows = conn.execute(comp3_query, params).fetchall()
    comp3_summaries = [dict(r) for r in comp3_rows]

    # Comparação com período anterior
    prev_comp3_summaries = []
    if previous_period:
        prev_query = "SELECT * FROM component_summaries WHERE period = ?"
        prev_params: list[Any] = [previous_period]
        if team_type and team_type != "todas":
            prev_query += " AND sg_equipe = ?"
            prev_params.append(team_type)
        prev_comp3_summaries = [dict(r) for r in conn.execute(prev_query, prev_params).fetchall()]

    # Indicadores detalhados de Qualidade
    ind_query = """
        SELECT period, sg_equipe, co_tipo_indicador, no_indicador,
               qtd_regular, qtd_suficiente, qtd_bom, qtd_otimo
        FROM quality_indicator_results
        WHERE period = ?
    """
    ind_params: list[Any] = [selected_period]
    if team_type and team_type != "todas":
        ind_query += " AND sg_equipe = ?"
        ind_params.append(team_type)
    ind_query += " ORDER BY sg_equipe, co_tipo_indicador"

    ind_rows = conn.execute(ind_query, ind_params).fetchall()

    # Indicadores do período anterior para tendência
    prev_ind_map: dict[tuple[str, int], dict[str, Any]] = {}
    if previous_period:
        prev_inds = conn.execute(
            """
            SELECT sg_equipe, co_tipo_indicador, qtd_regular, qtd_suficiente, qtd_bom, qtd_otimo
            FROM quality_indicator_results
            WHERE period = ?
            """,
            (previous_period,),
        ).fetchall()
        for pi in prev_inds:
            prev_ind_map[(pi["sg_equipe"], pi["co_tipo_indicador"])] = dict(pi)

    # Processar indicadores e identificar prioridades de atenção
    indicators = []
    attention_indicators = []

    for row in ind_rows:
        eq = row["sg_equipe"]
        co_tipo = row["co_tipo_indicador"]
        nome = row["no_indicador"]
        reg = row["qtd_regular"] or 0
        suf = row["qtd_suficiente"] or 0
        bom = row["qtd_bom"] or 0
        oti = row["qtd_otimo"] or 0
        total = reg + suf + bom + oti

        # Buscar peso na NT 8/2026
        peso = None
        cod_ind = None
        if eq in INDICADORES_PESOS:
            for k, meta in INDICADORES_PESOS[eq].items():
                if meta["coTipo"] == co_tipo or meta["nome"].lower() in nome.lower():
                    peso = meta["peso"]
                    cod_ind = k
                    break

        # Comparação com período anterior
        prev_data = prev_ind_map.get((eq, co_tipo))
        tendencia = "estavel"
        if prev_data:
            prev_favoravel = (prev_data.get("qtd_otimo", 0) or 0) + (prev_data.get("qtd_bom", 0) or 0)
            curr_favoravel = oti + bom
            if curr_favoravel > prev_favoravel:
                tendencia = "subiu"
            elif curr_favoravel < prev_favoravel:
                tendencia = "caiu"

        # Classificação predominante ou agregada
        if oti >= bom and oti >= suf and oti >= reg and oti > 0:
            predom = "Ótimo"
        elif bom >= suf and bom >= reg and bom > 0:
            predom = "Bom"
        elif suf >= reg and suf > 0:
            predom = "Suficiente"
        elif reg > 0:
            predom = "Regular"
        else:
            predom = "Indisponível"

        item = {
            "period": selected_period,
            "team_type": eq,
            "indicator_code": cod_ind or f"IND-{co_tipo}",
            "co_tipo_indicador": co_tipo,
            "name": nome,
            "peso": peso,
            "regular": reg,
            "suficiente": suf,
            "bom": bom,
            "otimo": oti,
            "total_teams": total,
            "predominant": predom,
            "trend": tendencia,
            "needs_attention": (reg > 0 or suf > 0 or tendencia == "caiu"),
        }
        indicators.append(item)

        if item["needs_attention"]:
            attention_indicators.append(item)

    # Calcular KPIs
    # Componente II: Em Pacujá, 100% das 3 equipes eSF são classificadas como Ótimo no CVAT
    c2_otimo_count = sum(r["qtd_otimo"] or 0 for r in cvat_dimensions if "Cadastro" in r["no_dimensao"])
    c2_total_count = sum((r["qtd_otimo"] or 0) + (r["qtd_bom"] or 0) + (r["qtd_suficiente"] or 0) + (r["qtd_regular"] or 0) for r in cvat_dimensions if "Cadastro" in r["no_dimensao"])
    c2_label = "100% Ótimo" if (c2_total_count > 0 and c2_otimo_count == c2_total_count) else ("Ótimo" if c2_otimo_count > 0 else "Indisponível")

    # Componente III: Percentual médio de Ótimo/Bom
    c3_total = sum(r["total_equipes"] or 0 for r in comp3_summaries)
    c3_otimo = sum(r["qtd_otimo"] or 0 for r in comp3_summaries)
    c3_bom = sum(r["qtd_bom"] or 0 for r in comp3_summaries)
    c3_regular = sum(r["qtd_regular"] or 0 for r in comp3_summaries)

    if c3_total > 0:
        c3_pct_favoravel = round(((c3_otimo + c3_bom) / c3_total) * 100, 1)
        c3_label = f"{c3_pct_favoravel}% Bom/Ótimo"
        c3_predominant = "Ótimo" if c3_otimo >= c3_bom else "Bom"
    else:
        c3_label = "—"
        c3_predominant = "Sem dados"

    # Time series de todos os quadrimestres
    time_series: dict[str, Any] = {"periods": available_periods, "teams": {}}
    for p in available_periods:
        p_rows = conn.execute(
            "SELECT sg_equipe, qtd_otimo, qtd_bom, qtd_suficiente, qtd_regular, total_equipes FROM component_summaries WHERE period = ?",
            (p,),
        ).fetchall()
        for pr in p_rows:
            eq = pr["sg_equipe"]
            if eq not in time_series["teams"]:
                time_series["teams"][eq] = {"otimo": [], "bom": [], "suficiente": [], "regular": []}
            time_series["teams"][eq]["otimo"].append(pr["qtd_otimo"] or 0)
            time_series["teams"][eq]["bom"].append(pr["qtd_bom"] or 0)
            time_series["teams"][eq]["suficiente"].append(pr["qtd_suficiente"] or 0)
            time_series["teams"][eq]["regular"].append(pr["qtd_regular"] or 0)

    last_sync_row = conn.execute("SELECT timestamp FROM sync_history ORDER BY id DESC LIMIT 1").fetchone()
    last_check_str = last_sync_row["timestamp"][:10] if last_sync_row else "—"

    conn.close()

    return {
        "period": selected_period,
        "available_periods": available_periods,
        "previous_period": previous_period,
        "kpis": {
            "component_2": {
                "title": "Vínculo e acompanhamento",
                "label": c2_label,
                "desc": f"3 equipes eSF avaliadas no {selected_period}",
                "class": "excellent",
            },
            "component_3": {
                "title": "Qualidade do cuidado",
                "label": c3_label,
                "predominant": c3_predominant,
                "desc": f"{c3_total} equipes com avaliação publicada",
                "class": "good" if c3_regular == 0 else "warning",
            },
            "teams_count": len(teams_list),
            "last_check": last_check_str,
        },
        "teams": teams_list,
        "cvat_dimensions": cvat_dimensions,
        "component_summaries": comp3_summaries,
        "indicators": indicators,
        "attention_indicators": attention_indicators,
        "time_series": time_series,
        "methodology": METODOLOGIA_INFO,
    }


def list_raw_files(db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT id, filename, report_type, component, period, source_url, fetched_at, file_size, sha256_hash, status, notes FROM raw_files ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_improvement_actions(status: str | None = None, db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM improvement_actions"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_improvement_action(data: dict[str, Any], db_path: Path | None = None) -> dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO improvement_actions (title, description, team_type, indicator_code, indicator_name, responsible, deadline, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("title", ""),
                data.get("description", ""),
                data.get("team_type", "Geral"),
                data.get("indicator_code"),
                data.get("indicator_name"),
                data.get("responsible", ""),
                data.get("deadline", ""),
                data.get("status", "pendente"),
                now,
                now,
            ),
        )
        action_id = cur.lastrowid
    conn.close()
    return {"id": action_id, "status": "created"}


def update_improvement_action(action_id: int, data: dict[str, Any], db_path: Path | None = None) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        cur = conn.execute(
            """
            UPDATE improvement_actions
            SET title = coalesce(?, title),
                description = coalesce(?, description),
                team_type = coalesce(?, team_type),
                indicator_code = coalesce(?, indicator_code),
                indicator_name = coalesce(?, indicator_name),
                responsible = coalesce(?, responsible),
                deadline = coalesce(?, deadline),
                status = coalesce(?, status),
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("title"),
                data.get("description"),
                data.get("team_type"),
                data.get("indicator_code"),
                data.get("indicator_name"),
                data.get("responsible"),
                data.get("deadline"),
                data.get("status"),
                now,
                action_id,
            ),
        )
        affected = cur.rowcount
    conn.close()
    return affected > 0


def delete_improvement_action(action_id: int, db_path: Path | None = None) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM improvement_actions WHERE id = ?", (action_id,))
        affected = cur.rowcount
    conn.close()
    return affected > 0


def get_executive_report_data(
    period: str | None = None,
    team_type: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Compila os dados consolidados para o relatório executivo oficial da APS Pacujá."""
    summary = get_dashboard_summary(period=period, team_type=team_type, db_path=db_path)
    actions = list_improvement_actions(db_path=db_path)
    raw_files = list_raw_files(db_path=db_path)

    # Identificar totalizadores para a liderança
    indicators = summary.get("indicators", [])
    otimo_count = sum(1 for ind in indicators if ind.get("predominant") == "Ótimo")
    bom_count = sum(1 for ind in indicators if ind.get("predominant") == "Bom")
    suficiente_count = sum(1 for ind in indicators if ind.get("predominant") == "Suficiente")
    regular_count = sum(1 for ind in indicators if ind.get("predominant") == "Regular")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "municipality": "Pacujá",
        "state": "CE",
        "ibge": "230990",
        "period": summary.get("period"),
        "available_periods": summary.get("available_periods", []),
        "previous_period": summary.get("previous_period"),
        "kpis": summary.get("kpis", {}),
        "teams": summary.get("teams", []),
        "indicators": indicators,
        "attention_indicators": summary.get("attention_indicators", []),
        "component_summaries": summary.get("component_summaries", []),
        "cvat_dimensions": summary.get("cvat_dimensions", []),
        "improvement_actions": actions,
        "raw_files": raw_files,
        "counts_by_concept": {
            "otimo": otimo_count,
            "bom": bom_count,
            "suficiente": suficiente_count,
            "regular": regular_count,
            "total": len(indicators),
        },
        "methodology": summary.get("methodology", {}),
    }


def get_monthly_tracking_status(db_path: Path | None = None) -> dict[str, Any]:
    """Fornece informações detalhadas sobre a rotina de acompanhamento e sincronização mês a mês."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        syncs = conn.execute(
            """
            SELECT id, timestamp, trigger_type, periods_found, files_downloaded, files_unchanged, status, message
            FROM sync_history
            ORDER BY id DESC
            LIMIT 12
            """
        ).fetchall()

        history = [dict(s) for s in syncs]
        last_sync = history[0] if history else None

        # Obter lista de quadrimestres e registros consolidados
        periods_rows = conn.execute(
            "SELECT DISTINCT period FROM component_summaries ORDER BY period DESC"
        ).fetchall()
        periods = [r["period"] for r in periods_rows]
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    # Próxima checagem programada (dia 5 do próximo mês às 06:00 UTC)
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    next_check = f"{next_year:04d}-{next_month:02d}-05T06:00:00Z"

    return {
        "status": "ativo",
        "frequency": "Mensal (todo dia 5 às 06:00 UTC e sob demanda)",
        "last_sync": last_sync,
        "next_scheduled_check": next_check,
        "total_periods_tracked": len(periods),
        "available_periods": periods,
        "recent_syncs": history,
    }

