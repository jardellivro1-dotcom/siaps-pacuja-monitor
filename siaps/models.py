from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path(root_dir: Path | None = None) -> Path:
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "siaps_monitor.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Habilita WAL mode e busy_timeout para permitir leituras e escritas concorrentes em banco compartilhado
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.OperationalError:
        pass
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript(
            """
            -- Tabelas do Domínio Siaps
            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                report_type TEXT NOT NULL,
                component TEXT NOT NULL,
                period TEXT,
                source_url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                periods_found TEXT NOT NULL,
                files_downloaded INTEGER NOT NULL,
                files_unchanged INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT
            );

            CREATE TABLE IF NOT EXISTS teams (
                co_equipe TEXT PRIMARY KEY,
                no_equipe TEXT NOT NULL,
                sg_equipe TEXT NOT NULL,
                municipio_ibge TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS component_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                sg_uf TEXT NOT NULL,
                ibge TEXT NOT NULL,
                municipio TEXT NOT NULL,
                component TEXT NOT NULL,
                sg_equipe TEXT NOT NULL,
                qtd_otimo INTEGER,
                pct_otimo REAL,
                qtd_bom INTEGER,
                pct_bom REAL,
                qtd_suficiente INTEGER,
                pct_suficiente REAL,
                qtd_regular INTEGER,
                pct_regular REAL,
                total_equipes INTEGER,
                raw_file_id INTEGER REFERENCES raw_files(id),
                UNIQUE(period, component, sg_equipe)
            );

            CREATE TABLE IF NOT EXISTS cvat_dimension_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                sg_uf TEXT NOT NULL,
                ibge TEXT NOT NULL,
                municipio TEXT NOT NULL,
                sg_equipe TEXT NOT NULL,
                co_tipo_indicador INTEGER,
                no_dimensao TEXT NOT NULL,
                qtd_otimo INTEGER,
                qtd_bom INTEGER,
                qtd_suficiente INTEGER,
                qtd_regular INTEGER,
                raw_file_id INTEGER REFERENCES raw_files(id),
                UNIQUE(period, sg_equipe, no_dimensao)
            );

            CREATE TABLE IF NOT EXISTS quality_indicator_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                sg_uf TEXT NOT NULL,
                ibge TEXT NOT NULL,
                municipio TEXT NOT NULL,
                sg_equipe TEXT NOT NULL,
                co_tipo_indicador INTEGER NOT NULL,
                no_indicador TEXT NOT NULL,
                qtd_regular INTEGER,
                qtd_suficiente INTEGER,
                qtd_bom INTEGER,
                qtd_otimo INTEGER,
                raw_file_id INTEGER REFERENCES raw_files(id),
                UNIQUE(period, sg_equipe, co_tipo_indicador)
            );

            CREATE TABLE IF NOT EXISTS improvement_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                team_type TEXT NOT NULL,
                indicator_code TEXT,
                indicator_name TEXT,
                responsible TEXT NOT NULL,
                deadline TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pendente', 'em_andamento', 'concluido')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Tabelas de Autenticação, Autorização e Auditoria (RBAC)
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT,
                role TEXT NOT NULL CHECK(role IN ('admin', 'coordenador_aps', 'equipe_saude', 'leitor')),
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                status TEXT NOT NULL DEFAULT 'success',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
            """
        )
    conn.close()
