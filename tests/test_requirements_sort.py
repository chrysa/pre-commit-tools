"""Tests for requirements_sort."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.requirements_sort import main, sort_requirements, sort_setup_cfg


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortRequirements:
    def test_sorted_unchanged(self) -> None:
        lines = ['requests', 'urllib3']
        assert sort_requirements(lines) == ['requests', 'urllib3']

    def test_unsorted_sorted(self) -> None:
        lines = ['urllib3', 'requests']
        assert sort_requirements(lines) == ['requests', 'urllib3']

    def test_comments_first(self) -> None:
        lines = ['urllib3', '# comment', 'requests']
        result = sort_requirements(lines)
        assert result[0] == '# comment'
        assert result[1:] == ['requests', 'urllib3']

    def test_blank_lines_first(self) -> None:
        lines = ['urllib3', '', 'requests']
        result = sort_requirements(lines)
        assert result[0] == ''
        assert result[1:] == ['requests', 'urllib3']

    def test_case_insensitive(self) -> None:
        lines = ['Urllib3', 'requests']
        result = sort_requirements(lines)
        assert result == ['requests', 'Urllib3']


class TestRequirementsSortMain:
    def test_already_sorted_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'req.txt', 'requests\nurllib3\n')
        assert main([f]) == 0

    def test_unsorted_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'req.txt', 'urllib3\nrequests\n')
        assert main([f]) == 1
        lines = Path(f).read_text().splitlines()
        assert lines[0] == 'requests'
        assert lines[1] == 'urllib3'

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0


_SETUP_CFG_SORTED = """\
[metadata]
name = my_package

[options]
python_requires = >=3.10

[options.extras_require]
alpha =
    aaa>=1.0
    bbb>=2.0
beta =
    ccc>=3.0
"""

_SETUP_CFG_UNSORTED_EXTRAS = """\
[metadata]
name = my_package

[options]
python_requires = >=3.10

[options.extras_require]
beta =
    ccc>=3.0
alpha =
    bbb>=2.0
    aaa>=1.0
"""

_SETUP_CFG_WITH_INSTALL = """\
[options]
install_requires =
    zlib
    requests
"""

_SETUP_CFG_WITH_INSTALL_SORTED = """\
[options]
install_requires =
    requests
    zlib
"""


class TestSortSetupCfg:
    def test_already_sorted_unchanged(self) -> None:
        assert sort_setup_cfg(_SETUP_CFG_SORTED) == _SETUP_CFG_SORTED

    def test_extras_keys_sorted(self) -> None:
        result = sort_setup_cfg(_SETUP_CFG_UNSORTED_EXTRAS)
        lines = result.splitlines()
        extra_keys = [ln.split('=')[0].strip() for ln in lines if ln and not ln.startswith((' ', '\t', '[', '#'))]
        # Only extras keys (non-metadata keys)
        extras = [k for k in extra_keys if k in ('alpha', 'beta')]
        assert extras == ['alpha', 'beta']

    def test_deps_within_extra_sorted(self) -> None:
        result = sort_setup_cfg(_SETUP_CFG_UNSORTED_EXTRAS)
        lines = result.splitlines()
        in_alpha = False
        alpha_deps: list[str] = []
        for ln in lines:
            if ln.strip() == 'alpha =':
                in_alpha = True
                continue
            if in_alpha:
                if ln.startswith((' ', '\t')):
                    alpha_deps.append(ln.strip())
                else:
                    break
        assert alpha_deps == ['aaa>=1.0', 'bbb>=2.0']

    def test_install_requires_sorted(self) -> None:
        assert sort_setup_cfg(_SETUP_CFG_WITH_INSTALL) == _SETUP_CFG_WITH_INSTALL_SORTED

    def test_install_requires_already_sorted_unchanged(self) -> None:
        assert sort_setup_cfg(_SETUP_CFG_WITH_INSTALL_SORTED) == _SETUP_CFG_WITH_INSTALL_SORTED


class TestRequirementsSortMainSetupCfg:
    def test_sorted_setup_cfg_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'setup.cfg', _SETUP_CFG_SORTED)
        assert main([f]) == 0

    def test_unsorted_setup_cfg_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'setup.cfg', _SETUP_CFG_UNSORTED_EXTRAS)
        assert main([f]) == 1
        result = Path(f).read_text(encoding='utf-8')
        lines = result.splitlines()
        extras = [ln.split('=')[0].strip() for ln in lines if ln.strip() in ('alpha =', 'beta =')]
        assert extras.index('alpha') < extras.index('beta')
