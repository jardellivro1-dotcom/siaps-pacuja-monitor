from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request, send_file

from siaps.calculations import METODOLOGIA_INFO, INDICADORES_PESOS
from siaps.ingestion import sync_siaps_data
from siaps.models import init_db, get_connection
from siaps.security import apply_security_headers, require_admin_if_configured
from siaps.services import (
    create_improvement_action,
    delete_improvement_action,
    get_dashboard_summary,
    get_executive_report_data,
    get_monthly_tracking_status,
    get_system_status,
    list_improvement_actions,
    list_raw_files,
    update_improvement_action,
)
from siaps.validators import (
    ValidationError,
    validate_action_payload,
    validate_csv_filename,
    validate_period,
    validate_team_type,
)

ROOT = Path(__file__).resolve().parent
RAW_DATA = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "siaps_monitor.db"
APP_VERSION = "1.0.0"


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SIAPS_SECRET_KEY", "dev-only-change-me"),
        RAW_DATA_DIR=RAW_DATA,
        DB_PATH=DB_PATH,
    )
    if test_config:
        app.config.update(test_config)

    # Garante inicialização do banco de dados
    init_db(Path(app.config["DB_PATH"]))

    @app.after_request
    def security_headers(response):
        return apply_security_headers(response)

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        return jsonify(error="Erro de validação.", message=str(err)), 400

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/healthz")
    def healthz():
        db_path = Path(app.config["DB_PATH"])
        db_ok = False
        try:
            conn = get_connection(db_path)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            db_ok = True
        except Exception:
            db_ok = False

        status_str = "ok" if db_ok else "degraded"
        return jsonify(
            status=status_str,
            application="Monitor APS Pacujá",
            version=APP_VERSION,
            database="connected" if db_ok else "disconnected",
            environment=os.environ.get("FLASK_ENV", "production" if not app.debug else "development"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ), (200 if db_ok else 503)

    @app.get("/api/status")
    def status():
        raw_dir = Path(app.config["RAW_DATA_DIR"])
        db_path = Path(app.config["DB_PATH"])
        res = get_system_status(db_path=db_path, raw_dir=raw_dir)
        res["app_version"] = APP_VERSION
        return jsonify(res)

    @app.get("/api/dashboard")
    def dashboard():
        raw_period = request.args.get("period")
        raw_team = request.args.get("team_type")

        # Validação rigorosa de entradas
        period = validate_period(raw_period)
        team_type = validate_team_type(raw_team)

        db_path = Path(app.config["DB_PATH"])
        summary = get_dashboard_summary(period=period, team_type=team_type, db_path=db_path)
        return jsonify(summary)

    @app.get("/api/teams")
    def teams():
        db_path = Path(app.config["DB_PATH"])
        conn = get_connection(db_path)
        rows = conn.execute("SELECT co_equipe, no_equipe, sg_equipe, updated_at FROM teams ORDER BY sg_equipe, no_equipe").fetchall()
        conn.close()
        return jsonify(teams=[dict(r) for r in rows])

    @app.get("/api/raw-files")
    def raw_files():
        db_path = Path(app.config["DB_PATH"])
        files = list_raw_files(db_path=db_path)
        return jsonify(files=files)

    @app.get("/api/raw-files/<filename>/download")
    def download_raw_file(filename: str):
        # Validação de nome e proteção contra path traversal
        clean_filename = validate_csv_filename(filename)
        raw_dir = Path(app.config["RAW_DATA_DIR"]).resolve()
        target = (raw_dir / clean_filename).resolve()

        if not target.is_relative_to(raw_dir) or not target.exists():
            abort(404, description="Arquivo CSV não encontrado.")

        return send_file(
            target,
            as_attachment=True,
            download_name=clean_filename,
            mimetype="text/csv",
        )

    @app.post("/api/sync")
    @require_admin_if_configured
    def sync():
        raw_dir = Path(app.config["RAW_DATA_DIR"])
        db_path = Path(app.config["DB_PATH"])
        trigger = request.json.get("trigger", "manual") if request.is_json else "manual"
        # Limita trigger string a valor seguro
        trigger_clean = str(trigger)[:30]
        result = sync_siaps_data(db_path=db_path, raw_dir=raw_dir, trigger_type=trigger_clean)

        if result.get("status") == "busy":
            return jsonify(result), 409
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    @app.get("/api/actions")
    def actions():
        db_path = Path(app.config["DB_PATH"])
        raw_status = request.args.get("status")
        status_filter = str(raw_status).strip().lower() if raw_status else None
        if status_filter and status_filter not in {"pendente", "em_andamento", "concluido"}:
            status_filter = None

        items = list_improvement_actions(status=status_filter, db_path=db_path)
        return jsonify(actions=items)

    @app.post("/api/actions")
    @require_admin_if_configured
    def create_action():
        db_path = Path(app.config["DB_PATH"])
        data = request.get_json(force=True) or {}
        cleaned_data = validate_action_payload(data, is_update=False)
        res = create_improvement_action(cleaned_data, db_path=db_path)
        return jsonify(res), 201

    @app.put("/api/actions/<int:action_id>")
    @require_admin_if_configured
    def update_action(action_id: int):
        db_path = Path(app.config["DB_PATH"])
        data = request.get_json(force=True) or {}
        cleaned_data = validate_action_payload(data, is_update=True)
        success = update_improvement_action(action_id, cleaned_data, db_path=db_path)
        if not success:
            return jsonify(error="Ação não encontrada."), 404
        return jsonify(status="updated")

    @app.delete("/api/actions/<int:action_id>")
    @require_admin_if_configured
    def delete_action(action_id: int):
        db_path = Path(app.config["DB_PATH"])
        success = delete_improvement_action(action_id, db_path=db_path)
        if not success:
            return jsonify(error="Ação não encontrada."), 404
        return jsonify(status="deleted")

    @app.get("/api/export/backup")
    def export_backup():
        """Exporta cópia integral de dados normalizados e auditoria para fins de backup e rastreabilidade."""
        db_path = Path(app.config["DB_PATH"])
        conn = get_connection(db_path)

        backup_data = {
            "application": "Monitor APS Pacujá",
            "version": APP_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "municipality": "Pacujá",
            "state": "CE",
            "ibge": "230990",
            "methodology": METODOLOGIA_INFO,
            "teams": [dict(r) for r in conn.execute("SELECT * FROM teams").fetchall()],
            "raw_files": [dict(r) for r in conn.execute("SELECT * FROM raw_files").fetchall()],
            "sync_history": [dict(r) for r in conn.execute("SELECT * FROM sync_history").fetchall()],
            "component_summaries": [dict(r) for r in conn.execute("SELECT * FROM component_summaries").fetchall()],
            "cvat_dimension_results": [dict(r) for r in conn.execute("SELECT * FROM cvat_dimension_results").fetchall()],
            "quality_indicator_results": [dict(r) for r in conn.execute("SELECT * FROM quality_indicator_results").fetchall()],
            "improvement_actions": [dict(r) for r in conn.execute("SELECT * FROM improvement_actions").fetchall()],
        }
        conn.close()

        payload_bytes = json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8")
        backup_hash = hashlib.sha256(payload_bytes).hexdigest()
        backup_data["sha256_integrity"] = backup_hash

        return jsonify(backup_data)

    @app.get("/api/methodology")
    def methodology():
        return jsonify(
            app_version=APP_VERSION,
            metodologia=METODOLOGIA_INFO,
            indicadores=INDICADORES_PESOS,
            limitacoes=[
                "Os indicadores representam agregação pública de desempenho das equipes e não constituem prontuário ou histórico individual de pacientes.",
                "Não é permitido inferir notas para tipos de equipe excluídos da NT 8/2026 (eAPP, eCR, eSFR).",
                "Ausência de dados é preservada como ausência e nunca convertida em zero.",
                "Resultados oficiais são de responsabilidade do Ministério da Saúde / Siaps."
            ]
        )

    @app.get("/relatorio")
    def relatorio_view():
        """Página visual e imprimível do Relatório Executivo da APS Pacujá."""
        raw_period = request.args.get("period")
        raw_team = request.args.get("team_type")
        period = validate_period(raw_period)
        team_type = validate_team_type(raw_team)

        db_path = Path(app.config["DB_PATH"])
        data = get_executive_report_data(period=period, team_type=team_type, db_path=db_path)
        return render_template("relatorio.html", report=data)

    @app.get("/api/relatorio")
    def api_relatorio():
        """Retorna dados estruturados do Relatório Executivo para exportação ou integração."""
        raw_period = request.args.get("period")
        raw_team = request.args.get("team_type")
        period = validate_period(raw_period)
        team_type = validate_team_type(raw_team)

        db_path = Path(app.config["DB_PATH"])
        data = get_executive_report_data(period=period, team_type=team_type, db_path=db_path)
        return jsonify(data)

    @app.get("/api/monthly-tracking")
    def monthly_tracking():
        """Status da rotina e histórico de acompanhamento mês a mês."""
        db_path = Path(app.config["DB_PATH"])
        return jsonify(get_monthly_tracking_status(db_path=db_path))

    @app.post("/api/sync/monthly")
    @require_admin_if_configured
    def sync_monthly():
        """Dispara verificação da rotina mensal de atualização dos dados públicos do Siaps."""
        raw_dir = Path(app.config["RAW_DATA_DIR"])
        db_path = Path(app.config["DB_PATH"])
        result = sync_siaps_data(db_path=db_path, raw_dir=raw_dir, trigger_type="rotina_mensal")
        if result.get("status") == "busy":
            return jsonify(result), 409
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
