"""
Daemon de Agendamento Independente para o Monitor APS Pacujá.
Executa como serviço em segundo plano no servidor (desvinculado de máquina pessoal),
gerenciando rotinas de sincronização mensal com o Siaps, backups automáticos e alertas.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backup_external import create_external_backup
from scripts.monthly_update import run_monthly_routine
from siaps.alerts import send_external_alert
from siaps.privacy import scan_database_for_privacy_violations

RUNNING = True


def _handle_signal(signum: int, frame: Any) -> None:
    global RUNNING
    print(f"\n[!] Sinal {signum} recebido. Encerrando o daemon com segurança...")
    RUNNING = False


def run_daemon() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    print("=" * 60)
    print("Daemon de Agendamento Independente - Monitor APS Pacujá")
    print("Serviço autônomo desvinculado de computador pessoal")
    print("=" * 60)
    print(f"Hora de início (UTC): {datetime.now(timezone.utc).isoformat()}")

    send_external_alert("info", "Daemon de Agendamento Iniciado", "O serviço independente de agendamento está ativo.")

    last_sync_month: int | None = None
    last_backup_day: int | None = None

    while RUNNING:
        now = datetime.now(timezone.utc)

        # 1. Rotina Mensal do Siaps: Todo dia 5 às 06:00 UTC
        if now.day == 5 and now.hour == 6 and last_sync_month != now.month:
            print(f"[{now.isoformat()}] Disparando rotina mensal do Siaps...")
            try:
                ret = run_monthly_routine()
                if ret == 0:
                    last_sync_month = now.month
                    send_external_alert("info", "Sincronização Mensal Concluída", f"Competência {now.year}-{now.month:02d} verificada com sucesso.")
                else:
                    send_external_alert("error", "Falha na Sincronização Mensal", "Erro ao sincronizar dados com o catálogo público do Siaps.")
            except Exception as e:
                send_external_alert("critical", "Exceção no Agendador Mensal", str(e))

        # 2. Rotina Diária de Backup Externo: Todos os dias às 03:00 UTC
        if now.hour == 3 and last_backup_day != now.day:
            print(f"[{now.isoformat()}] Executando rotina diária de backup externo...")
            try:
                b_res = create_external_backup()
                last_backup_day = now.day
                print(f"[OK] Backup diário gerado: {b_res['archive']}")

                # 3. Varredura LGPD diária após o backup
                p_res = scan_database_for_privacy_violations()
                if p_res["status"] != "conforme":
                    send_external_alert("warning", "Alerta de Privacidade LGPD", f"{p_res['total_violacoes']} violação(ões) detectada(s) no banco.")
            except Exception as e:
                send_external_alert("error", "Falha no Backup Diário", str(e))

        # Intervalo de verificação: 60 segundos
        time.sleep(60)

    print("[*] Daemon encerrado.")


if __name__ == "__main__":
    run_daemon()
