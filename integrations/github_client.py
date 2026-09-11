"""
Cliente mínimo para a API REST do GitHub.
Usa um Personal Access Token (env var GITHUB_TOKEN) com escopo 'repo'.

Docs: https://docs.github.com/en/rest/issues/issues
"""
from __future__ import annotations
import os
import requests

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, repo: str | None = None, token: str | None = None):
        # repo no formato "owner/nome-do-repo"
        self.repo = repo or os.environ["GITHUB_REPO"]
        self.token = token or os.environ["GITHUB_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def create_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict:
        url = f"{GITHUB_API}/repos/{self.repo}/issues"
        payload = {"title": title, "body": body, "labels": labels or []}
        resp = self.session.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def list_open_issues(self, label: str | None = None) -> list[dict]:
        url = f"{GITHUB_API}/repos/{self.repo}/issues"
        params = {"state": "open"}
        if label:
            params["labels"] = label
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
