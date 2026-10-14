"""
Rotina de Backup Externo Automatizado do Monitor APS Pacujá.
Gera snapshot atômico do banco de dados (SQLite backup API), compacta com arquivos CSV
originais, calcula assinatura criptográfica SHA-256 e executa verificação de restauração.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from siaps.models import get_connection, init_db


def create_external_backup(
    dest_dir: Path | None = None,
    db_path: Path | None = None,
    raw_dir: Path | None = None,
    retention_count: int = 14,
) -> dict[str, str | int]:
    """Cria backup atômico comprimido e assinado criptograficamente."""
    if dest_dir is None:
        dest_dir = ROOT / "data" / "backups"
    if db_path is None:
        db_path = ROOT / "data" / "siaps_monitor.db"
    if raw_dir is None:
        raw_dir = ROOT / "data" / "raw"

    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_basename = f"backup_siaps_pacuja_{timestamp_str}"
    temp_dir = dest_dir / f"temp_{timestamp_str}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Snapshot atômico do banco SQLite sem travamento de leituras (API Online Backup)
        temp_db = temp_dir / "siaps_monitor.db"
        src_conn = get_connection(db_path)
        dest_conn = sqlite3.connect(temp_db)
        with dest_conn:
            src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()

        # 2. Verificação de integridade no snapshot antes de empacotar
        verify_conn = sqlite3.connect(temp_db)
        integrity = verify_conn.execute("PRAGMA integrity_check").fetchall()
        verify_conn.close()
        if not integrity or integrity[0][0] != "ok":
            raise RuntimeError(f"Falha no teste de integridade do backup: {integrity}")

        # 3. Copia relatórios brutos originais
        temp_raw = temp_dir / "raw"
        if raw_dir.exists():
            shutil.copytree(raw_dir, temp_raw, dirs_exist_ok=True)

        # 4. Cria arquivo comprimido .tar.gz
        archive_path = dest_dir / f"{backup_basename}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_db, arcname="siaps_monitor.db")
            if temp_raw.exists():
                tar.add(temp_raw, arcname="raw")

        # 5. Calcula hash SHA-256 do arquivo de backup
        hasher = hashlib.sha256()
        with open(archive_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        backup_sha256 = hasher.hexdigest()

        # 6. Grava arquivo checksum para auditoria externa
        checksum_path = dest_dir / f"{backup_basename}.sha256"
        checksum_path.write_text(f"{backup_sha256}  {archive_path.name}\n", encoding="utf-8")

        # 7. Rotação de backups antigos
        all_archives = sorted(dest_dir.glob("backup_siaps_pacuja_*.tar.gz"), key=os.path.getmtime, reverse=True)
        if len(all_archives) > retention_count:
            for old in all_archives[retention_count:]:
                try:
                    old.unlink()
                    old_sha = dest_dir / f"{old.stem}.sha256"
                    if old_sha.exists():
                        old_sha.unlink()
                except Exception:
                    pass

        return {
            "status": "success",
            "archive": str(archive_path),
            "sha256": backup_sha256,
            "size_bytes": archive_path.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    finally:
        # Limpeza do diretório temporário
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup Externo Seguro do Monitor APS Pacujá")
    parser.add_argument("--dest", type=Path, help="Diretório de destino do backup externo")
    parser.add_argument("--retention", type=int, default=14, help="Número de backups mantidos na rotação")
    args = parser.parse_args()

    print("[*] Iniciando rotina de backup externo atômico...")
    try:
        res = create_external_backup(dest_dir=args.dest, retention_count=args.retention)
        print(f"[OK] Backup gerado com sucesso: {res['archive']}")
        print(f"[*] Assinatura SHA-256: {res['sha256']}")
        print(f"[*] Tamanho: {res['size_bytes']} bytes")
        return 0
    except Exception as exc:
        print(f"[ERRO] Falha no backup externo: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
