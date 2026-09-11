"""
Camada fina de acesso ao SQLite. Mantida separada do resto do agente
de propósito: o script de auditoria (validation/) importa este mesmo
módulo para ler os dados com a MESMA fonte de verdade que o agente usou
para escrever — evita discrepância boba por formato de dado diferente.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "findings.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def start_scan(repo: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO scans (repo, started_at, status) VALUES (?, ?, 'running')",
        (repo, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    scan_id = cur.lastrowid
    conn.close()
    return scan_id


def finish_scan(scan_id: int, status: str = "completed") -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE scans SET finished_at = ?, status = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), status, scan_id),
    )
    conn.commit()
    conn.close()


def add_finding(scan_id: int, **kwargs) -> int:
    conn = get_connection()
    kwargs["scan_id"] = scan_id
    kwargs["created_at"] = datetime.now(timezone.utc).isoformat()
    columns = ", ".join(kwargs.keys())
    placeholders = ", ".join("?" for _ in kwargs)
    cur = conn.execute(
        f"INSERT INTO findings ({columns}) VALUES ({placeholders})",
        tuple(kwargs.values()),
    )
    conn.commit()
    finding_id = cur.lastrowid
    conn.close()
    return finding_id


def set_issue_number(finding_id: int, issue_number: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE findings SET github_issue_number = ? WHERE id = ?",
        (issue_number, finding_id),
    )
    conn.commit()
    conn.close()
