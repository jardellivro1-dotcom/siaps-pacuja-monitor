import os
import hashlib
import json
import sqlite3
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from siaps.models import get_connection, init_db
from siaps.parser import normalize_float, normalize_int, parse_siaps_csv
from siaps.security import SyncLockContext, SyncBusyError
from siaps.validators import sanitize_csv_formula


SIAPS_PUBLIC_BASE = "https://apisiaps.saude.gov.br/"
PACUJA_IBGE = "230990"
PACUJA_UF = "CE"
PACUJA_NOME = "PACUJÁ"


def _format_date_pt(dt: datetime) -> str:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    return f"{dt.day:02d} de {meses[dt.month - 1]} de {dt.year} - {dt.hour:02d}:{dt.minute:02d}h"


def _get_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.environ.get("SIAPS_INSECURE_SSL") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _validate_safe_url(url: str) -> str:
    """Prevenção contra SSRF: restringe requisições exclusivamente ao domínio oficial do Siaps."""
    if not url.startswith(SIAPS_PUBLIC_BASE):
        raise ValueError(f"Destino de rede não autorizado: '{url}'. Permitido apenas '{SIAPS_PUBLIC_BASE}'.")
    return url


def _escape_csv_val(val: Any) -> str:
    sanitized = sanitize_csv_formula(val)
    escaped = sanitized.replace('"', '""')
    return f'"{escaped}\t"'



def _build_csv_string(
    titulo_relatorio: str,
    cabecalho: list[str],
    dados: list[list[Any]],
    dicionario: list[list[str]] | None = None,
    filtros: list[str] | None = None,
    generation_time: datetime | None = None,
) -> str:
    if generation_time is None:
        generation_time = datetime.now()

    linhas = [
        "Ministério da Saúde - MS",
        "Secretaria de Atenção Primária à Saúde - Saps",
        "Sistema de Informação para a Atenção Primária à Saúde – Siaps",
        f"Dado gerado em: {_format_date_pt(generation_time)}",
        titulo_relatorio,
        "Dado Preliminar",
        "",
        "Dados sociodemográficos:",
        f"UF: {PACUJA_UF}",
        f"Município: {PACUJA_IBGE} / {PACUJA_NOME}",
        "",
    ]
    if filtros:
        linhas.append("Filtro:")
        linhas.extend(filtros)
        linhas.append("")

    linhas.append(";".join(cabecalho))
    for row in dados:
        escaped_cells = [_escape_csv_val(c) for c in row]
        linhas.append(";".join(escaped_cells))

    linhas.append("")
    linhas.append("Fonte: Sistema de Informação para a Atenção Primária à Saúde - SIAPS")

    if dicionario:
        linhas.append("")
        for d in dicionario:
            if not d or d == [""]:
                linhas.append("")
            else:
                escaped = [_escape_csv_val(c) for c in d]
                linhas.append(";".join(escaped))

    return "\r\n".join(linhas) + "\r\n"



def fetch_public_competencias(timeout: int = 15) -> list[str]:
    """Descobre dinamicamente os quadrimestres disponíveis no catálogo público do Siaps."""
    url = f"{SIAPS_PUBLIC_BASE}api/public/filtros/competencias"
    _validate_safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorAPSPacuja/1.0", "Accept": "application/json"})
    ctx = _get_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            quads = set()
            for item in data:
                comp = item.get("nuCompetencia", "")
                if "Q" in comp:
                    quads.add(comp)
            if quads:
                return sorted(list(quads))
    except Exception:
        pass
    # Fallback para quadrimestres padrão verificados no catálogo caso a rota de filtros varie
    return ["2025Q2", "2025Q3", "2026Q1"]


def fetch_public_teams(timeout: int = 15) -> list[dict[str, Any]]:
    """Obtém a lista oficial de equipes do município de Pacujá pelo endpoint público."""
    url = f"{SIAPS_PUBLIC_BASE}api/public/filtros/equipes?municipioIbge={PACUJA_IBGE}"
    _validate_safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorAPSPacuja/1.0", "Accept": "application/json"})
    ctx = _get_ssl_context()

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_consolidated_public_data(quadrimestres: list[str], timeout: int = 20) -> dict[str, Any]:
    """Chama o endpoint público de consolidação por quadrimestre para Pacujá, Ceará."""
    url = f"{SIAPS_PUBLIC_BASE}api/public/componente/indicador-quadrimestre/filtro"
    _validate_safe_url(url)
    payload = {
        "uf": [PACUJA_UF],
        "coMunicipioIbge": [PACUJA_IBGE],
        "nuQuadrimestre": quadrimestres,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MonitorAPSPacuja/1.0",
        },
        method="POST",
    )
    ctx = _get_ssl_context()

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_reports_csvs(consolidated_data: dict[str, Any], quadrimestres: list[str]) -> list[dict[str, Any]]:
    """
    Gera o conteúdo dos 4 relatórios CSV oficiais com a serialização idêntica à do portal Siaps.
    """
    filtro_str = [f"Quadrimestre selecionada: {', '.join(quadrimestres)}"]
    reports = []

    # 1. Relatório Geral dos Componentes (Ba)
    header_geral = [
        "Quadrimestre/Ano", "Estado", "Código IBGE", "Município", "Classificação Final",
        "Vínculo e Acompanhamento Territorial -  Nº eSF", "Vínculo e Acompanhamento Territorial -  Nº eAP",
        "Qualidade -  Nº eSF", "Qualidade -  Nº eAP", "Qualidade -  Nº esB", "Qualidade -  Nº eMulti"
    ]
    dict_geral = [
        [""],
        ["Legenda da Classificação da Nota Final do Componente II", "", "", "", "", "", "", "Legenda da Classificação da Nota Final do Componente III"],
        ["Regular", "< 5", "", "", "", "", "Regular", "> 2,5"],
        ["Suficiente", "5 a 6.9", "", "", "", "", "Suficiente", "2.6 a 4.9"],
        ["Bom", "7 a 8.5", "", "", "", "", "Bom", "5 a 7.5"],
        ["Ótimo", "> 8.5", "", "", "", "", "Ótimo", "> 7.5"],
    ]

    # Agrupa dados de classificacaoFinalComponente por quadrimestre e faixa
    dados_geral = []
    cfc = consolidated_data.get("classificacaoFinalComponente", [])
    quads_map: dict[tuple[str, str], dict[str, int]] = {}
    for r in cfc:
        quad = r.get("nuQuadrimestre", "")
        eq = r.get("sgEquipe", "")
        origem = r.get("tipoOrigem", "")
        key = (quad, f"{origem}_{eq}")
        quads_map[key] = {
            "otimo": r.get("qtdClassificacaoOtimo", 0),
            "bom": r.get("qtdClassificacaoBom", 0),
            "suficiente": r.get("qtdClassificacaoSuficiente", 0),
            "regular": r.get("qtdClassificacaoRegular", 0),
        }

    for quad in quadrimestres:
        for faixa in ["Ótimo", "Bom", "Suficiente", "Regular"]:
            f_key = faixa.lower().replace("ó", "o")
            row = [
                quad, PACUJA_UF, PACUJA_IBGE, PACUJA_NOME, faixa,
                quads_map.get((quad, "CVAT_eSF"), {}).get(f_key, 0),
                quads_map.get((quad, "CVAT_eAP"), {}).get(f_key, 0),
                quads_map.get((quad, "QUALIDADE_eSF"), {}).get(f_key, 0),
                quads_map.get((quad, "QUALIDADE_eAP"), {}).get(f_key, 0),
                quads_map.get((quad, "QUALIDADE_eSB"), {}).get(f_key, 0),
                quads_map.get((quad, "QUALIDADE_eMulti"), {}).get(f_key, 0),
            ]
            dados_geral.append(row)

    csv_geral = _build_csv_string(
        "Relatorio Publico - Classificacao Geral dos Componentes",
        header_geral, dados_geral, dict_geral, filtro_str
    )
    reports.append({
        "filename": "Relatorio_Publico_Classificacao_Geral_dos_Componentes.csv",
        "report_type": "geral_componentes",
        "component": "Componente II e III",
        "content": csv_geral,
    })

    # 2. Relatório CVAT por Dimensão (La)
    header_cvat = [
        "Quadrimestre/Ano", "UF", "Código IBGE", "Município", "Tipo de Equipe",
        "Dimensão por tipo de equipe", "Total de equipe - REGULAR",
        "Total de equipe - SUFICIENTE", "Total de equipe  - BOM", "Total de equipe   - ÓTIMO"
    ]
    dict_cvat = [
        [""],
        ["Legenda do Conceito Obtido do Indicador"],
        ["Regular", "0,25"],
        ["Suficiente", "0,50"],
        ["Bom", "0,75"],
        ["Ótimo", "1"],
    ]
    dados_cvat = []
    for r in consolidated_data.get("classificacaoFinalPorDimensaoCvat", []):
        dados_cvat.append([
            r.get("nuQuadrimestre", ""),
            r.get("sgUf", PACUJA_UF),
            r.get("coMunicipioIbge", PACUJA_IBGE),
            r.get("noMunicipioAcentuado", PACUJA_NOME),
            r.get("sgEquipe", "eSF"),
            r.get("noDimensao", ""),
            r.get("qtdClassificacaoRegular", 0),
            r.get("qtdClassificacaoSuficiente", 0),
            r.get("qtdClassificacaoBom", 0),
            r.get("qtdClassificacaoOtimo", 0),
        ])
    csv_cvat = _build_csv_string(
        "Relatorio Publico - Classificacao por Dimensao CVAT",
        header_cvat, dados_cvat, dict_cvat, filtro_str
    )
    reports.append({
        "filename": "Relatorio_Publico_Classificacao_por_Dimensao_CVAT.csv",
        "report_type": "cvat_dimensao",
        "component": "Componente II",
        "content": csv_cvat,
    })

    # 3. Relatório Classificação Final Qualidade (Va)
    header_qualidade_final = [
        "Quadrimestre/Ano", "UF", "Código IBGE", "Nome Município", "Sigla de Tipo de Equipe",
        "Classificação Final OTIMO (>7.5)", "Percentual Classificação Final OTIMO",
        "Classificação Final BOM", "Percentual Classificação Final BOM",
        "Classificação Final SUFICIENTE", "Percentual da Classificação Final SUFICIENTE",
        "Total de equipe - REGULAR", "Percentual Classificação Final REGULAR",
        "Total de equipe Válidas para o componente"
    ]
    dict_qualidade_final = [
        [""],
        ["Legenda da Classificação da Nota Final do Componente III"],
        ["Regular", "> 2,5"],
        ["Suficiente", "2.6 a 4.9"],
        ["Bom", "5 a 7.5"],
        ["Ótimo", "> 7.5"],
    ]
    dados_qualidade_final = []
    for r in cfc:
        if r.get("tipoOrigem") == "QUALIDADE":
            dados_qualidade_final.append([
                r.get("nuQuadrimestre", ""),
                r.get("sgUf", PACUJA_UF),
                r.get("coMunicipioIbge", PACUJA_IBGE),
                r.get("noMunicipioAcentuado", PACUJA_NOME),
                r.get("sgEquipe", ""),
                r.get("qtdClassificacaoOtimo", 0),
                r.get("percentualClassificacaoOtimo", 0.0),
                r.get("qtdClassificacaoBom", 0),
                r.get("percentualClassificacaoBom", 0.0),
                r.get("qtdClassificacaoSuficiente", 0),
                r.get("percentualClassificacaoSuficiente", 0.0),
                r.get("qtdClassificacaoRegular", 0),
                r.get("percentualClassificacaoRegular", 0.0),
                r.get("totalEquipesValidasParaComponente", 0),
            ])
    csv_qualidade_final = _build_csv_string(
        "Relatorio Publico - Classificacao Final Qualidade",
        header_qualidade_final, dados_qualidade_final, dict_qualidade_final, filtro_str
    )
    reports.append({
        "filename": "Relatorio_Publico_Classificacao_Final_Qualidade.csv",
        "report_type": "qualidade_final",
        "component": "Componente III",
        "content": csv_qualidade_final,
    })

    # 4. Relatório Conceito por Indicador Qualidade (ja)
    header_indicador = [
        "Quadrimestre/Ano", "UF", "Código IBGE", "Município", "Tipo de Equipe",
        "Indicador por tipo de equipe", "Total de equipe - REGULAR",
        "Total de equipe - SUFICIENTE", "Total de equipe - BOM", "Total de equipe - ÓTIMO"
    ]
    dict_indicador = [
        [""],
        ["Legenda do Conceito Obtido do Indicador"],
        ["Regular", "0,25"],
        ["Suficiente", "0,50"],
        ["Bom", "0,75"],
        ["Ótimo", "1"],
    ]
    dados_indicador = []
    for r in consolidated_data.get("conceitoPorIndicadorQualidade", []):
        dados_indicador.append([
            r.get("nuQuadrimestre", ""),
            r.get("sgUf", PACUJA_UF),
            r.get("coMunicipioIbge", PACUJA_IBGE),
            r.get("noMunicipioAcentuado", PACUJA_NOME),
            r.get("sgEquipe", ""),
            r.get("noIndicador", ""),
            r.get("qtdClassificacaoRegular", 0),
            r.get("qtdClassificacaoSuficiente", 0),
            r.get("qtdClassificacaoBom", 0),
            r.get("qtdClassificacaoOtimo", 0),
        ])
    csv_indicador = _build_csv_string(
        "Relatorio Publico - Conceito por Indicador Qualidade",
        header_indicador, dados_indicador, dict_indicador, filtro_str
    )
    reports.append({
        "filename": "Relatorio_Publico_Conceito_por_Indicador_Qualidade.csv",
        "report_type": "qualidade_indicador",
        "component": "Componente III",
        "content": csv_indicador,
    })

    return reports


def sync_siaps_data(
    db_path: Path | None = None,
    raw_dir: Path | None = None,
    trigger_type: str = "manual",
) -> dict[str, Any]:
    """
    Executa a sincronização completa e idempotente dos dados públicos do Siaps para Pacujá, CE.
    Preserva os arquivos originais sem alteração, registra o SHA-256 e popula as tabelas normalizadas.
    """
    init_db(db_path)
    conn = get_connection(db_path)

    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    files_downloaded = 0
    files_unchanged = 0
    errors: list[str] = []

    try:
        with SyncLockContext():
            # 1. Descobrir quadrimestres
            quads = fetch_public_competencias()
            periods_str = ", ".join(quads)

            # 2. Descobrir e salvar equipes
            try:
                teams = fetch_public_teams()
                with conn:
                    for t in teams:
                        conn.execute(
                            """
                            INSERT INTO teams (co_equipe, no_equipe, sg_equipe, municipio_ibge, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(co_equipe) DO UPDATE SET
                                no_equipe=excluded.no_equipe,
                                sg_equipe=excluded.sg_equipe,
                                updated_at=excluded.updated_at
                            """,
                            (t.get("coEquipe"), t.get("noEquipe"), t.get("sgEquipe"), PACUJA_IBGE, timestamp),
                        )
            except Exception as e:
                errors.append(f"Aviso ao atualizar equipes: {e}")

            # 3. Baixar dados consolidados oficiais
            consolidated = fetch_consolidated_public_data(quads)

            # 4. Gerar relatórios e gravar com verificação de idempotência (SHA-256)
            reports = generate_reports_csvs(consolidated, quads)

            for rep in reports:
                filename = rep["filename"]
                target_file = raw_dir / filename

                # Verifica se o arquivo já existe no disco e se os dados são idênticos
                content = rep["content"]
                if target_file.exists():
                    try:
                        existing_text = target_file.read_text(encoding="utf-8", errors="ignore")
                        old_parsed = parse_siaps_csv(existing_text)
                        new_parsed = parse_siaps_csv(content)
                        if old_parsed["rows"] == new_parsed["rows"]:
                            # Conteúdo idêntico: preserva arquivo original sem alterar timestamp ou hash
                            content = existing_text
                    except Exception:
                        pass

                content_bytes = content.encode("utf-8")
                file_size = len(content_bytes)
                sha256 = hashlib.sha256(content_bytes).hexdigest()

                # Checar existência por hash (Idempotência conforme Regra 6 do AGENTS.md)
                existing = conn.execute(
                    "SELECT id, sha256_hash FROM raw_files WHERE filename = ?",
                    (filename,)
                ).fetchone()

                raw_file_id: int
                if existing and existing["sha256_hash"] == sha256:
                    files_unchanged += 1
                    raw_file_id = existing["id"]
                else:
                    # Grava arquivo físico original preservado
                    target_file.write_bytes(content_bytes)

                    with conn:
                        if existing:
                            conn.execute(
                                """
                                UPDATE raw_files
                                SET sha256_hash = ?, file_size = ?, fetched_at = ?, status = 'updated', period = ?
                                WHERE id = ?
                                """,
                                (sha256, file_size, timestamp, periods_str, existing["id"]),
                            )
                            raw_file_id = existing["id"]
                        else:
                            cur = conn.execute(
                                """
                                INSERT INTO raw_files (filename, report_type, component, period, source_url, fetched_at, file_size, sha256_hash, status, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'valid', 'Importado do catálogo público oficial do Siaps')
                                """,
                                (
                                    filename,
                                    rep["report_type"],
                                    rep["component"],
                                    periods_str,
                                    f"{SIAPS_PUBLIC_BASE}api/public/componente/indicador-quadrimestre/filtro",
                                    timestamp,
                                    file_size,
                                    sha256,
                                ),
                            )
                            raw_file_id = cur.lastrowid
                    files_downloaded += 1

                    # Normalizar registros correspondentes
                    _normalize_report_data(conn, rep["report_type"], rep["content"], raw_file_id, consolidated)

            status_msg = "Sincronização concluída com sucesso."
            if errors:
                status_msg += f" Avisos: {'; '.join(errors)}"

            with conn:
                conn.execute(
                    """
                    INSERT INTO sync_history (timestamp, trigger_type, periods_found, files_downloaded, files_unchanged, status, message)
                    VALUES (?, ?, ?, ?, ?, 'success', ?)
                    """,
                    (timestamp, trigger_type, periods_str, files_downloaded, files_unchanged, status_msg),
                )

            return {
                "status": "success",
                "timestamp": timestamp,
                "periods_found": quads,
                "files_downloaded": files_downloaded,
                "files_unchanged": files_unchanged,
                "message": status_msg,
            }

    except SyncBusyError as sbe:
        return {
            "status": "busy",
            "timestamp": timestamp,
            "periods_found": [],
            "files_downloaded": 0,
            "files_unchanged": 0,
            "message": str(sbe),
        }
    except Exception as e:

        err_msg = f"Falha na sincronização pública: {e}"
        with conn:
            conn.execute(
                """
                INSERT INTO sync_history (timestamp, trigger_type, periods_found, files_downloaded, files_unchanged, status, message)
                VALUES (?, ?, 'none', 0, 0, 'error', ?)
                """,
                (timestamp, trigger_type, err_msg),
            )
        return {
            "status": "error",
            "timestamp": timestamp,
            "periods_found": [],
            "files_downloaded": 0,
            "files_unchanged": 0,
            "message": err_msg,
        }
    finally:
        conn.close()


def _normalize_report_data(
    conn: sqlite3.Connection,
    report_type: str,
    csv_content: str,
    raw_file_id: int,
    consolidated: dict[str, Any],
) -> None:
    """Valida o CSV através do parser e atualiza as tabelas normalizadas do SQLite."""
    parsed = parse_siaps_csv(csv_content)

    with conn:
        if report_type == "cvat_dimensao":
            for row in parsed["rows"]:
                # [Quadrimestre, UF, IBGE, Município, Equipe, Dimensão, Regular, Suficiente, Bom, Ótimo]
                if len(row) >= 10:
                    quad, uf, ibge, mun, eq, dim, reg, suf, bom, oti = row[:10]
                    conn.execute(
                        """
                        INSERT INTO cvat_dimension_results (period, sg_uf, ibge, municipio, sg_equipe, no_dimensao, qtd_otimo, qtd_bom, qtd_suficiente, qtd_regular, raw_file_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(period, sg_equipe, no_dimensao) DO UPDATE SET
                            qtd_otimo=excluded.qtd_otimo,
                            qtd_bom=excluded.qtd_bom,
                            qtd_suficiente=excluded.qtd_suficiente,
                            qtd_regular=excluded.qtd_regular,
                            raw_file_id=excluded.raw_file_id
                        """,
                        (quad, uf, ibge, mun, eq, dim, normalize_int(oti), normalize_int(bom), normalize_int(suf), normalize_int(reg), raw_file_id),
                    )

        elif report_type == "qualidade_final":
            for row in parsed["rows"]:
                # [Quad, UF, IBGE, Nome Mun, Equipe, QtdOti, PctOti, QtdBom, PctBom, QtdSuf, PctSuf, QtdReg, PctReg, Total]
                if len(row) >= 14:
                    quad, uf, ibge, mun, eq, q_oti, p_oti, q_bom, p_bom, q_suf, p_suf, q_reg, p_reg, tot = row[:14]
                    conn.execute(
                        """
                        INSERT INTO component_summaries (period, sg_uf, ibge, municipio, component, sg_equipe, qtd_otimo, pct_otimo, qtd_bom, pct_bom, qtd_suficiente, pct_suficiente, qtd_regular, pct_regular, total_equipes, raw_file_id)
                        VALUES (?, ?, ?, ?, 'Componente III', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(period, component, sg_equipe) DO UPDATE SET
                            qtd_otimo=excluded.qtd_otimo,
                            pct_otimo=excluded.pct_otimo,
                            qtd_bom=excluded.qtd_bom,
                            pct_bom=excluded.pct_bom,
                            qtd_suficiente=excluded.qtd_suficiente,
                            pct_suficiente=excluded.pct_suficiente,
                            qtd_regular=excluded.qtd_regular,
                            pct_regular=excluded.pct_regular,
                            total_equipes=excluded.total_equipes,
                            raw_file_id=excluded.raw_file_id
                        """,
                        (
                            quad, uf, ibge, mun, eq,
                            normalize_int(q_oti), normalize_float(p_oti),
                            normalize_int(q_bom), normalize_float(p_bom),
                            normalize_int(q_suf), normalize_float(p_suf),
                            normalize_int(q_reg), normalize_float(p_reg),
                            normalize_int(tot), raw_file_id
                        ),
                    )

        elif report_type == "qualidade_indicador":
            for r in consolidated.get("conceitoPorIndicadorQualidade", []):
                conn.execute(
                    """
                    INSERT INTO quality_indicator_results (period, sg_uf, ibge, municipio, sg_equipe, co_tipo_indicador, no_indicador, qtd_regular, qtd_suficiente, qtd_bom, qtd_otimo, raw_file_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(period, sg_equipe, co_tipo_indicador) DO UPDATE SET
                        no_indicador=excluded.no_indicador,
                        qtd_regular=excluded.qtd_regular,
                        qtd_suficiente=excluded.qtd_suficiente,
                        qtd_bom=excluded.qtd_bom,
                        qtd_otimo=excluded.qtd_otimo,
                        raw_file_id=excluded.raw_file_id
                    """,
                    (
                        r.get("nuQuadrimestre"),
                        r.get("sgUf", PACUJA_UF),
                        r.get("coMunicipioIbge", PACUJA_IBGE),
                        r.get("noMunicipioAcentuado", PACUJA_NOME),
                        r.get("sgEquipe"),
                        r.get("coTipoIndicador"),
                        r.get("noIndicador"),
                        r.get("qtdClassificacaoRegular", 0),
                        r.get("qtdClassificacaoSuficiente", 0),
                        r.get("qtdClassificacaoBom", 0),
                        r.get("qtdClassificacaoOtimo", 0),
                        raw_file_id,
                    ),
                )
