"""
Padrões de detecção de segredos expostos em código.
Escopo deliberadamente pequeno e com baixo falso-positivo para ser
fácil de auditar manualmente (comparar com validation/audit_findings.py).
"""
import re

# (nome_do_padrao, regex, severidade)
SECRET_PATTERNS = [
    ("AWS Access Key ID", re.compile(r"AKIA[0-9A-Z]{16}"), "CRITICAL"),
    ("GitHub Personal Access Token", re.compile(r"ghp_[A-Za-z0-9]{36}"), "CRITICAL"),
    ("GitHub Fine-grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "CRITICAL"),
    ("Slack Webhook URL", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+"), "HIGH"),
    ("Generic Private Key", re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"), "CRITICAL"),
    (
        "Hardcoded password assignment",
        re.compile(r"(?i)(password|passwd|pwd)\s*=\s*[\"'][^\"'\s]{6,}[\"']"),
        "MEDIUM",
    ),
    (
        "Generic API key assignment",
        re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"']"),
        "HIGH",
    ),
]

# Extensões de arquivo que vale a pena varrer (evita binários, node_modules etc.)
SCANNABLE_EXTENSIONS = {".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".txt", ".md", ".sh"}
IGNORED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
