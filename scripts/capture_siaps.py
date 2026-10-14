#!/usr/bin/env python3
"""
Script de captura e sincronização dos relatórios públicos oficiais do Siaps para Pacujá, Ceará.
Conforme as regras do AGENTS.md e arquitetura.md:
- Consulta apenas o catálogo e endpoints públicos do Siaps.
- Sem credenciais ou acessos restritos.
- Preserva arquivos originais com registro de SHA-256 e URL.
- Execução idempotente.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importação do pacote siaps
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from siaps.ingestion import sync_siaps_data
from siaps.models import get_db_path


def main() -> int:
    print("=" * 60)
    print("Monitor APS Pacujá - Captura e Auditoria Oficial Siaps")
    print("=" * 60)

    db_path = get_db_path(ROOT_DIR)
    raw_dir = ROOT_DIR / "data" / "raw"

    print(f"Diretório de arquivos brutos: {raw_dir}")
    print(f"Banco de dados: {db_path}")
    print("Iniciando descoberta de períodos e sincronização pública...")

    result = sync_siaps_data(db_path=db_path, raw_dir=raw_dir, trigger_type="cli")

    if result["status"] == "success":
        print("\nSincronização realizada com sucesso!")
        print(f"Quadrimestres encontrados: {', '.join(result['periods_found'])}")
        print(f"Novos arquivos gravados: {result['files_downloaded']}")
        print(f"Arquivos inalterados (idempotentes): {result['files_unchanged']}")
        print(f"Mensagem: {result['message']}")
        return 0
    else:
        print(f"\nErro na sincronização: {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
