"""Tests for dependabot_classified_deps."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from pre_commit_hooks.dependabot_classified_deps import main, sync

_DEPENDABOT = """\
version: 2
updates:
  - package-ecosystem: pip
    directory: /
    groups:
      alpha-stack:
        patterns:
          - alpha*
          - alphakit*
      beta-stack:
        patterns:
          - betapkg
          - betatool
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _managed(path: Path, group: str = 'misc') -> list[str] | None:
    config = YAML().load(path.read_text(encoding='utf-8'))
    groups = config['updates'][0]['groups']
    return list(groups[group]['patterns']) if group in groups else None


def _setup(tmp_path: Path, requires: str, dependabot: str = _DEPENDABOT) -> tuple[Path, Path]:
    cfg = tmp_path / 'setup.cfg'
    dep = tmp_path / '.github' / 'dependabot.yml'
    _write(cfg, f'[options]\ninstall_requires =\n{requires}')
    _write(dep, dependabot)
    return cfg, dep


class TestSync:
    def test_all_classified_no_managed_group(self, tmp_path: Path) -> None:
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    betapkg==2.0\n')
        unclassified, changed = sync(dep, [cfg])
        assert unclassified == []
        assert changed is False
        assert _managed(dep) is None

    def test_new_package_added_to_managed_group(self, tmp_path: Path) -> None:
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    gammapkg==0.1\n')
        unclassified, changed = sync(dep, [cfg])
        assert unclassified == ['gammapkg']
        assert changed is True
        assert _managed(dep) == ['gammapkg']

    def test_removed_package_pruned_and_group_dropped(self, tmp_path: Path) -> None:
        dependabot = _DEPENDABOT + '      misc:\n        patterns:\n          - gammapkg\n'
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n', dependabot)
        unclassified, changed = sync(dep, [cfg])
        assert unclassified == []
        assert changed is True
        assert _managed(dep) is None

    def test_managed_group_updated_when_members_change(self, tmp_path: Path) -> None:
        dependabot = _DEPENDABOT + '      misc:\n        patterns:\n          - gammapkg\n'
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    deltapkg==3.0\n', dependabot)
        unclassified, changed = sync(dep, [cfg])
        assert unclassified == ['deltapkg']
        assert changed is True
        assert _managed(dep) == ['deltapkg']

    def test_idempotent_when_already_synced(self, tmp_path: Path) -> None:
        dependabot = _DEPENDABOT + '      misc:\n        patterns:\n          - gammapkg\n'
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    gammapkg==0.1\n', dependabot)
        _, changed = sync(dep, [cfg])
        assert changed is False

    def test_semantic_group_globs_untouched(self, tmp_path: Path) -> None:
        cfg, dep = _setup(tmp_path, '    alpha-plugin==1.0  # extension\n    betatool>=2.0\n')
        unclassified, changed = sync(dep, [cfg])
        assert unclassified == []
        assert changed is False

    def test_missing_dependabot_is_noop(self, tmp_path: Path) -> None:
        cfg = tmp_path / 'setup.cfg'
        _write(cfg, '[options]\ninstall_requires =\n    gammapkg==0.1\n')
        assert sync(tmp_path / '.github' / 'dependabot.yml', [cfg]) == ([], False)


class TestMain:
    def _args(self, cfg: Path, dep: Path, *extra: str) -> list[str]:
        return ['--dependabot', str(dep), '--manifest', str(cfg), *extra]

    def test_returns_0_when_all_classified(self, tmp_path: Path) -> None:
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n')
        assert main(self._args(cfg, dep)) == 0

    def test_returns_1_when_config_mutated(self, tmp_path: Path) -> None:
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    gammapkg==0.1\n')
        assert main(self._args(cfg, dep)) == 1
        assert _managed(dep) == ['gammapkg']

    def test_strict_fails_on_stable_unclassified(self, tmp_path: Path) -> None:
        dependabot = _DEPENDABOT + '      misc:\n        patterns:\n          - gammapkg\n'
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    gammapkg==0.1\n', dependabot)
        assert main(self._args(cfg, dep)) == 1

    def test_allow_unclassified_passes_when_stable(self, tmp_path: Path) -> None:
        dependabot = _DEPENDABOT + '      misc:\n        patterns:\n          - gammapkg\n'
        cfg, dep = _setup(tmp_path, '    alpha-core==1.0\n    gammapkg==0.1\n', dependabot)
        assert main(self._args(cfg, dep, '--allow-unclassified')) == 0
