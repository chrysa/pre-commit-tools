# Deep-dive: chrysa/pre-commit-tools

**Repo local:** `/home/anthony/Documents/perso/projects/chrysa/pre-commit-tools`
**But (1 phrase):** Une collection maison de ~70 hooks pre-commit (paquet PyPI `pre_commit_hooks_tools`, Python 3.14, MIT) qui détecte les anti-patterns de qualité de code et de sécurité à travers plusieurs langages/écosystèmes (Python, TS/JS, CSS, Django/FastAPI, Docker, Helm, fichiers config, assets Claude) et applique les standards chrysa au moment du commit.

## Contexte projet

- Publié sur PyPI sous `pre-commit-hooks-tools`, consommé via `.pre-commit-config.yaml` par les autres repos chrysa.
- Chaque hook = un module `pre_commit_hooks/<name>.py` avec un `main()` exposé en `[project.scripts]`, déclaré dans `.pre-commit-hooks.yaml` (24 Ko, ~70 hooks).
- Beaucoup de hooks sont des détecteurs regex/AST simples (print/pprint/console.log, bare except, unreachable code, mutable defaults, CORS allow-all, hardcoded secrets, dockerfile no-latest, etc.), plus des "gates" (adr-gate, regression-gate, docs-drift-gate, quality-gate) et des sorters (yaml/json/requirements/ignore-file).
- C'est un OUTIL INTERNE dont la catégorie (collection de hooks pre-commit) a des équivalents OSS très établis. Les références ci-dessous sont surtout des sources de patterns d'implémentation (AST-based checks, secret detection, gates) plutôt que des dépendances à adopter.

---

## 1. pre-commit/pre-commit-hooks

- **owner/repo:** pre-commit/pre-commit-hooks
- **stars:** 6.7k
- **activité:** actif (maintenu, ~1204 commits, CI récente)
- **langage:** Python
- **licence:** **MIT** — COPIABLE
- **fichier/module précis du pattern:** `pre_commit_hooks/check_json.py`, `pre_commit_hooks/debug_statement_hook.py`, `pre_commit_hooks/end_of_file_fixer.py`
- **mécanisme réel:** Le canon du genre. Chaque hook = un module avec `def main(argv: Sequence[str] | None = None) -> int:` qui prend les fichiers en argv, retourne 1 si violation (0 sinon), et imprime un message par fichier. `debug_statement_hook.py` utilise `ast.walk` pour repérer `import pdb` / `breakpoint()` — exactement le pattern des détecteurs Python de pre-commit-tools.
- **snippet portable:**
  ```python
  import argparse, ast
  from collections.abc import Sequence

  DEBUG_NAMES = frozenset({"pdb", "ipdb", "breakpoint"})

  def check_file(filename: str) -> int:
      with open(filename, "rb") as f:
          tree = ast.parse(f.read(), filename=filename)
      rc = 0
      for node in ast.walk(tree):
          if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "breakpoint":
              print(f"{filename}:{node.lineno}: breakpoint() found")
              rc = 1
      return rc

  def main(argv: Sequence[str] | None = None) -> int:
      parser = argparse.ArgumentParser()
      parser.add_argument("filenames", nargs="*")
      args = parser.parse_args(argv)
      return max((check_file(f) for f in args.filenames), default=0)
  ```
- **intégration dans ce projet:** déjà le pattern exact utilisé. Utile pour aligner la signature `main(argv)`, la convention de code retour, et la structure `.pre-commit-hooks.yaml` (id/entry/language/types). Reprendre leurs conventions de `args_from_argv` et `types: [python]` pour filtrer les fichiers.
- **gotchas:** ils passent à `ast.parse` avec le nom de fichier (meilleurs messages d'erreur) ; gérer `SyntaxError` proprement (un fichier non parseable ne doit pas crasher le hook). Attention `language: python` vs `language: system` dans le yaml — pre-commit-tools s'installe en paquet donc `python`/`python3.14`.

## 2. asottile/pyupgrade

- **owner/repo:** asottile/pyupgrade
- **stars:** 4.1k
- **activité:** actif (auteur = mainteneur core de pre-commit)
- **langage:** Python
- **licence:** **MIT** — COPIABLE
- **fichier/module précis du pattern:** `pyupgrade/_data.py` (registry de plugins par type de nœud AST), `pyupgrade/_main.py` (token-based rewriting)
- **mécanisme réel:** Va plus loin que la détection : il RÉÉCRIT. Combine `ast` (pour comprendre la structure) et `tokenize-rt` (pour réécrire sans détruire le formatage/commentaires). Un registry mappe `ast.Call`/`ast.Import` → fonctions de callback qui yield des offsets à patcher. C'est le modèle à suivre pour les hooks de pre-commit-tools qui MODIFIENT (yaml-sorter, json-sorter, requirements-sort, format-dockerfile, generate-changelog) plutôt que juste détecter.
- **snippet portable:**
  ```python
  # AST pour trouver + tokenize-rt pour réécrire en préservant le style
  from tokenize_rt import src_to_tokens, tokens_to_src, Offset
  def rewrite(src: str, offsets: dict) -> str:
      tokens = src_to_tokens(src)
      for i, tok in reversed(list(enumerate(tokens))):
          if Offset(tok.offset[0], tok.offset[1]) in offsets:
              tokens[i] = tok._replace(src=offsets[Offset(*tok.offset)])
      return tokens_to_src(tokens)
  ```
- **intégration dans ce projet:** pour tout hook "fixer", séparer détection (AST) et réécriture (tokens) au lieu de regex-replace destructif. Adopter `tokenize-rt` si un hook doit modifier du Python sans casser commentaires/formatage.
- **gotchas:** parcourir les offsets en ordre inverse pour ne pas invalider les positions ; le token-rewriting est verbeux — ne l'employer que quand `ast.unparse` (qui perd les commentaires) ne suffit pas.

## 3. Yelp/detect-secrets

- **owner/repo:** Yelp/detect-secrets
- **stars:** 4.6k
- **activité:** actif
- **langage:** Python
- **licence:** **Apache-2.0** — COPIABLE (garder l'attribution NOTICE)
- **fichier/module précis du pattern:** `detect_secrets/plugins/` (un plugin par type de secret), `detect_secrets/core/baseline.py` (le mécanisme `.secrets.baseline`)
- **mécanisme réel:** Modèle plugin + baseline. Chaque détecteur hérite de `RegexBasedDetector` avec `denylist` de regex compilées ; un calcul d'entropie (Shannon) réduit les faux positifs. Le fichier `.secrets.baseline` (présent dans ce repo !) enregistre les secrets connus/audités pour ne pas re-signaler. Directement pertinent pour `django_hardcoded_secret.py` et `ts_hardcoded_secret.py`.
- **snippet portable:**
  ```python
  import math
  def shannon_entropy(data: str) -> float:
      if not data:
          return 0.0
      freq = {c: data.count(c) / len(data) for c in set(data)}
      return -sum(p * math.log2(p) for p in freq.values())

  # secret probable si high-entropy string dans un contexte assignation
  HIGH_ENTROPY = 4.5  # base64 ~4.5-6.0
  ```
- **intégration dans ce projet:** ajouter un filtre d'entropie aux hooks `*-hardcoded-secret` pour couper les faux positifs (les regex seules signalent trop). Réutiliser le format `.secrets.baseline` déjà présent pour une allowlist auditée partagée.
- **gotchas:** l'entropie seule sur-signale les hashes/UUID — combiner avec un contexte (nom de variable contenant `key`/`token`/`secret`/`password`). Apache-2.0 : conserver le NOTICE si tu copies du code substantiel.

## 4. gitleaks/gitleaks

- **owner/repo:** gitleaks/gitleaks
- **stars:** 28.7k
- **activité:** **feature-complete** — seulement patches sécurité désormais (auteur passe à "Betterleaks")
- **langage:** Go
- **licence:** **MIT** — COPIABLE (mais Go, pas directement portable en Python)
- **fichier/module précis du pattern:** `config/gitleaks.toml` (le catalogue de règles regex), `.gitleaks.toml` (présent dans ce repo)
- **mécanisme réel:** Détection de secrets par règles TOML déclaratives (regex + entropy + allowlist + path filters). L'intérêt ici n'est pas le code Go mais le **format de règles externalisées en TOML** — au lieu de hardcoder les patterns dans chaque module Python. Ce repo a déjà un `.gitleaks.toml`.
- **snippet portable (format de règle à imiter en config):**
  ```toml
  [[rules]]
  id = "django-secret-key"
  regex = '''SECRET_KEY\s*=\s*["'][^"']{20,}["']'''
  entropy = 3.5
  [rules.allowlist]
  regexes = ['''SECRET_KEY\s*=\s*os\.environ''']
  ```
- **intégration dans ce projet:** externaliser les patterns des détecteurs secrets/anti-patterns dans un fichier de config (TOML/YAML) chargé par les modules, plutôt qu'en constantes Python — cohérent avec le hook maison `no-external-tool-config` / la politique "no hardcoded constants" des règles chrysa. Le hook `no_hardcoded_localhost` pourrait aussi suivre ce modèle.
- **gotchas:** feature-complete = ne pas en dépendre pour du neuf ; c'est une source d'inspiration de format, pas une lib à vendorer. Regex Go (RE2) ≠ regex Python (`re`) — pas de lookbehind en RE2, adapter.

## 5. hadolint/hadolint

- **owner/repo:** hadolint/hadolint
- **stars:** 12.4k
- **activité:** actif
- **langage:** Haskell
- **licence:** **GPL-3.0** — **COPYLEFT → RÉIMPLÉMENTER (ne pas copier le code, seulement l'idée)**
- **fichier/module précis du pattern:** `src/Hadolint/Rule/` (une règle par fichier, ex. `DL3007` = no `latest` tag), parse le Dockerfile en AST.
- **mécanisme réel:** Parse le Dockerfile en AST puis applique des règles typées sur les instructions (FROM/RUN/USER/HEALTHCHECK). Couvre EXACTEMENT le domaine des hooks Docker de ce repo : `dockerfile_no_latest` (=DL3007), `dockerfile_non_root_user` (=DL3002/USER), `dockerfile_healthcheck`, `dockerfile_multi_stage_check`, `format_dockerfile`.
- **snippet portable (réimplémentation Python, pas copié):**
  ```python
  # parser léger d'instructions Dockerfile ligne-continuée
  def parse_instructions(text: str):
      logical, buf = [], ""
      for line in text.splitlines():
          s = line.rstrip()
          if s.endswith("\\"):
              buf += s[:-1] + " "
          else:
              logical.append((buf + s).strip()); buf = ""
      return [l for l in logical if l and not l.startswith("#")]

  def check_no_latest(instrs):
      return [i for i in instrs if i.upper().startswith("FROM") and ":latest" in i or
              (i.upper().startswith("FROM") and ":" not in i.split()[1])]
  ```
- **intégration dans ce projet:** aligner les numéros/messages de règles Docker sur la nomenclature hadolint (DL3007, etc.) pour familiarité ; réimplémenter la logique de parsing multi-ligne proprement plutôt qu'en regex naïve.
- **gotchas:** **GPL-3.0 — interdiction de copier du code source ; réimplémenter from scratch depuis la description des règles (documentées sur le wiki hadolint).** Gérer les `FROM ... AS builder` (multi-stage), `--platform`, et les args `FROM ${BASE}`.

## 6. astral-sh/ruff

- **owner/repo:** astral-sh/ruff
- **stars:** 49.2k
- **activité:** très actif
- **langage:** Rust
- **licence:** **MIT** — COPIABLE (mais Rust)
- **fichier/module précis du pattern:** `crates/ruff_linter/src/rules/` (une règle = un check + un fix optionnel), rule codes type `PLR0915`, `C901`
- **mécanisme réel:** Linter Python ultra-rapide couvrant 900+ règles avec autofix. Pertinent ici car les règles chrysa (`thresholds.md`) délèguent DÉJÀ complexité/longueur à Ruff (`PLR0915`, `C901`, `E501`, `PLR0913`). Plusieurs hooks maison (`python_mutable_default`, `no_bare_except`, `python_untyped_raise`) dupliquent des règles Ruff existantes (`B006`, `E722`, etc.).
- **snippet portable (mapping des doublons):**
  ```text
  python-mutable-default   ≈ Ruff B006 (mutable-argument-default)
  no-bare-except           ≈ Ruff E722 (bare-except)
  python-print-detection   ≈ Ruff T201 (print found)
  python-unreachable-code  ≈ Ruff (pyflakes) / vulture
  ```
- **intégration dans ce projet:** audit de déduplication — pour chaque hook Python maison, vérifier si une règle Ruff couvre déjà le cas ; si oui, soit supprimer le hook (déléguer à Ruff), soit le documenter comme complément volontaire. Réduit la surface de maintenance.
- **gotchas:** code Rust non portable ; l'intérêt est la carte de couverture, pas le code. Ruff ne vérifie PAS l'ordre des méthodes de classe (`class-design.md`) ni les READMEs de dossier — ces hooks maison restent justifiés.

## 7. semgrep/semgrep

- **owner/repo:** semgrep/semgrep
- **stars:** 16.2k
- **activité:** actif (commercial CE + platform)
- **langage:** OCaml (+ CLI Python)
- **licence:** **LGPL-2.1** — **COPYLEFT (faible) : utilisable comme outil, ne pas linker/copier le code source dans un dérivé propriétaire ; les RÈGLES YAML sont réutilisables**
- **fichier/module précis du pattern:** `rules/` communautaires (`p/python`, `p/django`, `p/react`) — patterns déclaratifs style-code
- **mécanisme réel:** Static analysis multi-langage par pattern-matching sémantique (30+ langages) : on écrit une règle qui ressemble au code cible avec des métavariables `$X`. Couvre le domaine multi-langage exact de ce repo (Python + TS/JS + CSS + React) avec UN moteur au lieu de N modules regex. Ex. `django-no-raw-sql`, `fastapi-missing-response-model`, `react-direct-dom`, `no-sync-in-async` sont tous exprimables en règles Semgrep.
- **snippet portable (règle YAML remplaçant un module):**
  ```yaml
  rules:
    - id: django-no-raw-sql
      languages: [python]
      severity: ERROR
      message: "Raw SQL détecté — utiliser l'ORM"
      pattern-either:
        - pattern: $CURSOR.execute(...)
        - pattern: django.db.connection.cursor()
  ```
- **intégration dans ce projet:** pour les nouveaux checks sémantiques multi-langage (surtout inter-fichiers ou nécessitant flow analysis, comme "hardcoded constants" que `enforcement-plan.md` juge trop bruyant en regex), envisager un hook wrapper `semgrep --config <rules>` plutôt que d'écrire un module AST par cas. Garder les modules Python natifs pour les checks triviaux (rapidité/zéro-dépendance).
- **gotchas:** LGPL-2.1 : OK d'invoquer le binaire et de distribuer tes propres règles YAML ; NE PAS copier de code source OCaml/Python dans les modules maison. Ajoute une dépendance lourde — à réserver aux checks qui le justifient. Cross-file analysis = Pro (payant).

---

## Synthèse licences

| Source | Licence | Verdict |
| --- | --- | --- |
| pre-commit-hooks | MIT | Copiable |
| pyupgrade | MIT | Copiable |
| detect-secrets | Apache-2.0 | Copiable (garder NOTICE) |
| gitleaks | MIT | Copiable (Go, format only) |
| **hadolint** | **GPL-3.0** | **Réimplémenter — copyleft fort** |
| ruff | MIT | Copiable (Rust, map only) |
| **semgrep** | **LGPL-2.1** | **Outil OK / règles OK ; ne pas copier le source** |

## Recommandations prioritaires (quick wins d'abord)

1. **Dédup Ruff** (quick) : retirer/marquer les hooks Python qui doublonnent des règles Ruff (`python-mutable-default`→B006, `no-bare-except`→E722, `python-print-detection`→T201).
2. **Entropie sur les hooks secrets** (quick) : ajouter le filtre Shannon de detect-secrets à `django_hardcoded_secret` / `ts_hardcoded_secret` pour couper les faux positifs.
3. **Externaliser les patterns** (medium) : sortir les regex des modules vers de la config (format gitleaks TOML), cohérent avec `no-external-tool-config` maison.
4. **Aligner les règles Docker sur hadolint** (medium, réimplémenter) : nomenclature DL#### + parsing multi-ligne robuste, sans copier de code GPL.
5. **Semgrep pour le multi-langage sémantique** (large) : n'y aller que pour les checks flow-sensitive difficiles en regex.
