"""coverage_ratchet — pre-commit hook.

Objectif :
    Quand la couverture réelle d'un package dépasse durablement le seuil déclaré
    dans la config CI (`coverage-threshold`), ouvrir automatiquement une GitHub
    issue `ratchet: <pkg> <lang> coverage now at N%` pour inviter à remonter le
    seuil.

Fonctionnement :
    1. Détecte la langue du repo (Python via coverage.xml, JS/TS via
       coverage/coverage-summary.json ou lcov.info).
    2. Lit le seuil déclaré dans .github/workflows/ci.yml (clé coverage-threshold).
    3. Si coverage_réelle - seuil ≥ MARGIN (2% par défaut) → action.
    4. Action : soit ouvre une GitHub issue par package (via `gh issue create`),
       soit imprime une recommandation si `gh` n'est pas disponible.
    5. Ne BLOQUE PAS le commit (exit 0 toujours — c'est du signal, pas un gate).

Invocation :
    pre-commit install
    pre-commit run coverage-ratchet-hook --all-files

Variables d'environnement :
    COVERAGE_RATCHET_MARGIN   (default 2)   — delta minimal pour déclencher
    COVERAGE_RATCHET_DRYRUN   (default 0)   — 1 = pas d'issue, juste afficher
    GH_TOKEN                  (optionnel)   — pour `gh issue create`

Exit codes :
    0 — toujours (même si aucune issue créée). Le hook n'est jamais bloquant.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

MARGIN = int(os.environ.get('COVERAGE_RATCHET_MARGIN', '2'))
DRYRUN = os.environ.get('COVERAGE_RATCHET_DRYRUN', '0') == '1'

CI_FILE_CANDIDATES = (
    Path('.github/workflows/ci.yml'),
    Path('.github/workflows/ci-python.yml'),
    Path('.github/workflows/ci-node.yml'),
    Path('.github/workflows/quality-checks.yml'),
)


@dataclass
class Report:
    package: str
    language: str
    actual: float
    threshold: int

    @property
    def delta(self) -> int:
        return int(self.actual) - self.threshold

    def should_ratchet(self) -> bool:
        return self.delta >= MARGIN


# ─── Detection ──────────────────────────────────────────────────────────────


def read_threshold() -> int | None:
    """Parse coverage-threshold: N dans n'importe quel workflow CI du repo."""
    import re

    pattern = re.compile(r'coverage-threshold:\s*(\d+)')
    for candidate in CI_FILE_CANDIDATES:
        if candidate.exists():
            match = pattern.search(candidate.read_text(encoding='utf-8'))
            if match:
                return int(match.group(1))
    return None


def detect_python_coverage() -> float | None:
    """Retourne la couverture Python globale en % ou None."""
    coverage_xml = Path('coverage.xml')
    if not coverage_xml.exists():
        return None
    try:
        root = ET.parse(coverage_xml).getroot()
        line_rate = float(root.get('line-rate', 0))
        return round(line_rate * 100, 2)
    except (ET.ParseError, ValueError):
        return None


def detect_node_coverage() -> float | None:
    """Retourne la couverture Node/JS/TS globale en % ou None."""
    summary = Path('coverage/coverage-summary.json')
    if summary.exists():
        try:
            data = json.loads(summary.read_text(encoding='utf-8'))
            return round(float(data['total']['lines']['pct']), 2)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    lcov = Path('coverage/lcov.info')
    if lcov.exists():
        lines = lcov.read_text(encoding='utf-8').splitlines()
        total = sum(1 for l in lines if l.startswith('DA:'))
        hit = sum(1 for l in lines if l.startswith('DA:') and int(l.split(',')[1]) > 0)
        if total > 0:
            return round(hit * 100 / total, 2)
    return None


def detect_reports() -> list[Report]:
    """Construit les rapports par langage présent dans le repo."""
    threshold = read_threshold()
    if threshold is None:
        return []

    reports: list[Report] = []
    package = Path.cwd().name

    if (py_cov := detect_python_coverage()) is not None:
        reports.append(
            Report(package=package, language='python', actual=py_cov, threshold=threshold),
        )

    if (node_cov := detect_node_coverage()) is not None:
        reports.append(
            Report(package=package, language='node', actual=node_cov, threshold=threshold),
        )

    return reports


# ─── Action : GitHub issue ──────────────────────────────────────────────────


def issue_title(report: Report) -> str:
    return f'ratchet: {report.package} ({report.language}) coverage now at {report.actual}% — threshold still {report.threshold}%'


def issue_body(report: Report) -> str:
    new_suggested = int(report.actual) - 1
    return (
        f'Detected by coverage-ratchet-hook (pre-commit).\n\n'
        f'- Package : `{report.package}`\n'
        f'- Langage : {report.language}\n'
        f'- Couverture actuelle : **{report.actual}%**\n'
        f'- Seuil déclaré (`coverage-threshold` CI) : {report.threshold}%\n'
        f'- Delta : **+{report.delta} pts** (margin requise {MARGIN})\n\n'
        f'### Action\n\n'
        f'Passer `coverage-threshold` de {report.threshold} à **{new_suggested}** '
        f'(floor(actual) − 1 pour garder 1% de buffer).\n\n'
        f'Dans `.github/workflows/ci.yml` :\n\n'
        f'```yaml\n'
        f'    with:\n'
        f'      coverage-threshold: {new_suggested}\n'
        f'```\n\n'
        f'_Issue générée automatiquement. Sera ré-ouverte par le hook si toujours vraie après correction._\n'
    )


def issue_already_open(title: str) -> bool:
    """Vérifie si une issue du même titre existe déjà (évite les doublons)."""
    try:
        out = subprocess.run(
            ['gh', 'issue', 'list', '--state', 'open', '--limit', '100', '--json', 'title'],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if out.returncode != 0:
            return False
        for entry in json.loads(out.stdout or '[]'):
            if entry.get('title') == title:
                return True
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return False
    return False


def create_github_issue(report: Report) -> bool:
    title = issue_title(report)
    body = issue_body(report)

    if issue_already_open(title):
        print(f'[ratchet]   ✓ issue déjà ouverte : {title}')
        return True

    if DRYRUN:
        print(f'[ratchet]   DRYRUN — aurait ouvert : {title}')
        return True

    try:
        out = subprocess.run(
            [
                'gh',
                'issue',
                'create',
                '--title',
                title,
                '--body',
                body,
                '--label',
                'coverage-ratchet,chore',
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if out.returncode == 0:
            print(f'[ratchet]   ✓ issue créée : {out.stdout.strip()}')
            return True
        print(f'[ratchet]   ⚠ échec gh issue create: {out.stderr.strip()}', file=sys.stderr)
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print(
            f'[ratchet]   ⚠ `gh` indisponible — recommandation seulement : {title}',
            file=sys.stderr,
        )
        return False


# ─── Entrypoint ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    reports = detect_reports()
    if not reports:
        return 0  # pas de rapport de coverage → rien à faire

    any_ratchet = False
    for report in reports:
        if not report.should_ratchet():
            print(
                f'[ratchet] {report.package} ({report.language}) : '
                f'{report.actual}% vs threshold {report.threshold}% — delta {report.delta} < margin {MARGIN}',
            )
            continue
        any_ratchet = True
        print(
            f'[ratchet] 🎯 {report.package} ({report.language}) : '
            f'coverage={report.actual}% dépasse threshold={report.threshold}% de {report.delta} pts',
        )
        create_github_issue(report)

    if not any_ratchet:
        print('[ratchet] Rien à remonter (tous les packages dans la marge).')

    return 0  # ne bloque JAMAIS le commit


if __name__ == '__main__':
    raise SystemExit(main())
