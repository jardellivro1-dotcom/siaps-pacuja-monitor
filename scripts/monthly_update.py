"""
Script de execução periódica (mês a mês) para sincronização e auditoria oficial dos dados públicos do Siaps em Pacujá/CE.
Projetado para execução agendada (Cron, Windows Task Scheduler ou GitHub Actions).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from siaps.ingestion import sync_siaps_data
from siaps.models import init_db


def run_monthly_routine() -> int:
    db_path = Path(os.environ.get("DATABASE_PATH", str(ROOT / "data" / "siaps_monitor.db")))
    raw_dir = Path(os.environ.get("RAW_DATA_DIR", str(ROOT / "data" / "raw")))

    print(f"[{datetime.now(timezone.utc).isoformat()}] Iniciando rotina mensal de verificação do Siaps...")
    print(f"Território: Pacujá, Ceará (IBGE 230990) · Catálogo Público Oficial")
    print(f"Banco de dados: {db_path}")
    print(f"Diretório de arquivos brutos: {raw_dir}")

    init_db(db_path)

    try:
        result = sync_siaps_data(db_path=db_path, raw_dir=raw_dir, trigger_type="rotina_mensal")
        status = result.get("status")
        msg = result.get("message")
        downloaded = result.get("files_downloaded", 0)
        unchanged = result.get("files_unchanged", 0)

        print(f"Resultado da rotina: STATUS={status.upper()}")
        print(f"Mensagem: {msg}")
        print(f"Arquivos novos/reprocessados: {downloaded} | Arquivos inalterados (mesmo SHA-256): {unchanged}")

        if status == "success":
            print("[OK] Rotina mensal concluida com integridade comprovada.")
            return 0
        elif status == "busy":
            print("[AVISO] Rotina interrompida: outra sincronizacao ja estava em andamento (mutex ativo).")
            return 0
        else:
            print(f"[ERRO] Erro na rotina mensal: {msg}")
            return 1

    except Exception as exc:
        print(f"[ERRO] Excecao na rotina mensal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_monthly_routine())
