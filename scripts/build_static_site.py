"""
Script de Geração de Site Estático para Publicação no GitHub Pages
Monitor APS Pacujá (IBGE 230990)

Exporta todos os dados processados e auditados em formato JSON estático,
renderiza os templates HTML com caminhos relativos e empacota os ativos
em 'dist/' para publicação no GitHub Pages (gh-pages) ou CDN estática.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from siaps.calculations import INDICADORES_PESOS, METODOLOGIA_INFO
from siaps.ingestion import sync_siaps_data
from siaps.models import get_connection, init_db
from siaps.services import (
    get_dashboard_summary,
    get_executive_report_data,
    get_monthly_tracking_status,
    get_system_status,
    list_improvement_actions,
    list_raw_files,
)

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DATA_RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "siaps_monitor.db"


def build_static_site(dest_dir: Path = DIST, db_path: Path = DB_PATH) -> dict[str, int]:
    print(f"=== Construindo Site Estático para GitHub Pages em {dest_dir} ===")

    # 1. Garante banco de dados populado
    init_db(db_path)
    conn = get_connection(db_path)
    t_count = conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
    conn.close()

    if t_count == 0 and DATA_RAW.exists():
        print("Populando banco de dados a partir dos relatórios públicos oficiais...")
        sync_siaps_data(db_path=db_path, raw_dir=DATA_RAW, trigger_type="static_build")

    # 2. Prepara diretório de destino limpo
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Cria .nojekyll para o GitHub Pages processar todos os diretórios e arquivos
    (dest_dir / ".nojekyll").write_text("", encoding="utf-8")

    # 3. Copia ativos estáticos (CSS, JS, imagens)
    dest_static = dest_dir / "static"
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, dest_static)
        print(f"Ativos estáticos copiados para {dest_static}")

    # 4. Cria estrutura de API estática
    api_dir = dest_dir / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    raw_files_api_dir = api_dir / "raw-files"
    raw_files_api_dir.mkdir(parents=True, exist_ok=True)
    dest_data_raw = dest_dir / "data" / "raw"
    dest_data_raw.mkdir(parents=True, exist_ok=True)

    # 5. Exporta status do sistema e períodos disponíveis
    status_data = get_system_status(db_path=db_path, raw_dir=DATA_RAW)
    status_data["app_version"] = "1.0.0"
    status_data["hosting_mode"] = "github_pages_static"
    (api_dir / "status.json").write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta lista de equipes
    conn = get_connection(db_path)
    teams_rows = [dict(r) for r in conn.execute("SELECT co_equipe, no_equipe, sg_equipe, updated_at FROM teams ORDER BY sg_equipe, no_equipe").fetchall()]
    conn.close()
    (api_dir / "teams.json").write_text(json.dumps({"teams": teams_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta rotina mês a mês
    monthly_data = get_monthly_tracking_status(db_path=db_path)
    (api_dir / "monthly-tracking.json").write_text(json.dumps(monthly_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta lista de arquivos brutos auditados
    raw_files = list_raw_files(db_path=db_path)
    (api_dir / "raw-files.json").write_text(json.dumps({"files": raw_files}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta metodologia
    methodology_data = {
        "app_version": "1.0.0",
        "metodologia": METODOLOGIA_INFO,
        "indicadores": INDICADORES_PESOS,
        "limitacoes": [
            "Os indicadores representam agregação pública de desempenho das equipes e não constituem prontuário ou histórico individual de pacientes.",
            "Não é permitido inferir notas para tipos de equipe excluídos da NT 8/2026 (eAPP, eCR, eSFR).",
            "Ausência de dados é preservada como ausência e nunca convertida em zero.",
            "Resultados oficiais são de responsabilidade do Ministério da Saúde / Siaps."
        ]
    }
    (api_dir / "methodology.json").write_text(json.dumps(methodology_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta sessão anônima padrão para api/auth/me
    auth_me_data = {"authenticated": False, "user": None}
    (api_dir / "auth").mkdir(exist_ok=True)
    (api_dir / "auth" / "me.json").write_text(json.dumps(auth_me_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Exporta ações de melhoria
    actions_data = list_improvement_actions(db_path=db_path)
    (api_dir / "actions.json").write_text(json.dumps({"actions": actions_data}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6. Copia arquivos CSV brutos para download estático
    csv_count = 0
    if DATA_RAW.exists():
        for csv_file in DATA_RAW.glob("*.csv"):
            shutil.copy2(csv_file, dest_data_raw / csv_file.name)
            # Salva também como rota de download direto em api/raw-files/<nome>/download
            dl_dir = raw_files_api_dir / csv_file.name
            dl_dir.mkdir(exist_ok=True)
            shutil.copy2(csv_file, dl_dir / "download")
            csv_count += 1
    print(f"{csv_count} arquivos CSV oficiais copiados para distribuição pública.")

    # 7. Pré-renderiza todas as permutações de dashboards (períodos x tipos de equipes)
    available_periods = [None] + status_data.get("available_periods", [])
    team_types = ["todas", "eSF", "eSB", "eMulti"]
    dash_count = 0

    for period in available_periods:
        for team in team_types:
            summary = get_dashboard_summary(period=period, team_type=team, db_path=db_path)
            p_key = period or "default"
            filename = f"dashboard_{p_key}_{team}.json"
            (api_dir / filename).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            dash_count += 1

            if period is None and team == "todas":
                (api_dir / "dashboard.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{dash_count} visualizações analíticas de dashboard exportadas em JSON.")

    # 8. Renderização dos Templates Jinja2 para HTML Estático
    jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    # Custom url_for helper para assets estáticos relativos
    def static_url_for(endpoint: str, filename: str = "") -> str:
        if endpoint == "static":
            return f"./static/{filename}"
        return f"./{filename}"

    jinja_env.globals["url_for"] = static_url_for

    # Renderiza index.html
    index_tpl = jinja_env.get_template("index.html")
    index_html = index_tpl.render(
        current_user=None,
        relatorio_url="relatorio.html",
        login_url="login.html",
    )
    (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
    (dest_dir / "404.html").write_text(index_html, encoding="utf-8")

    # Renderiza relatorio.html com os dados mais recentes do quadrimestre
    report_data = get_executive_report_data(period=None, team_type="todas", db_path=db_path)
    relatorio_tpl = jinja_env.get_template("relatorio.html")
    relatorio_html = relatorio_tpl.render(
        report=report_data,
        current_user=None,
    )
    (dest_dir / "relatorio.html").write_text(relatorio_html, encoding="utf-8")

    # Renderiza login.html
    login_tpl = jinja_env.get_template("login.html")
    login_html = login_tpl.render(current_user=None)
    (dest_dir / "login.html").write_text(login_html, encoding="utf-8")

    print(f"Páginas index.html, relatorio.html, login.html e 404.html compiladas com sucesso em {dest_dir}.")
    print("=== Site Estático Gerado com Sucesso! ===")

    return {
        "dashboards_exported": dash_count,
        "csv_files_copied": csv_count,
    }


if __name__ == "__main__":
    build_static_site()
