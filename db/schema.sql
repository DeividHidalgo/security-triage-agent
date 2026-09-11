-- Schema do banco de achados de segurança.
-- Cada linha é um "finding" reportado pelo agente. O script de auditoria
-- (validation/audit_findings.py) reprocessa essa tabela de forma independente
-- para confirmar que o agente não inventou nem esqueceu nada.

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running'   -- running | completed | failed
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id),
    kind TEXT NOT NULL,                -- 'dependency' | 'secret'
    package TEXT,                      -- nome do pacote (para dependency)
    installed_version TEXT,
    vulnerability_id TEXT,             -- ex: CVE/GHSA/OSV id
    severity TEXT NOT NULL,            -- CRITICAL | HIGH | MEDIUM | LOW
    file_path TEXT,
    line_number INTEGER,
    description TEXT,
    source_url TEXT,
    github_issue_number INTEGER,       -- preenchido se uma issue foi aberta
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
