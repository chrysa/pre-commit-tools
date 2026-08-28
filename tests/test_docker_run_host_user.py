"""Tests for the docker-run-host-user hook."""

from pre_commit_hooks.docker_run_host_user import detect_root_repo_mounts


def test_flags_repo_mount_without_user():
    source = (
        'sdk-generate:\n'
        '\t@docker run --rm -v "$(PWD)":/w -w /w/frontend node:22-alpine sh -c "npx x"\n'
    )
    violations = detect_root_repo_mounts(source, 'Makefile')
    assert len(violations) == 1
    assert violations[0][1] == 2
    assert '--user' in violations[0][2]


def test_accepts_explicit_user():
    source = '\t@docker run --rm --user $(shell id -u):$(shell id -g) -v "$(PWD)":/w img cmd\n'
    assert detect_root_repo_mounts(source, 'Makefile') == []


def test_accepts_short_user_flag():
    source = '\tdocker run --rm -u "$(id -u):$(id -g)" -v .:/code img cmd\n'
    assert detect_root_repo_mounts(source, 'run.sh') == []


def test_ignores_named_volume():
    source = '\tdocker run --rm -v tool-caches:/caches img cmd\n'
    assert detect_root_repo_mounts(source, 'Makefile') == []


def test_ignores_docker_compose():
    source = '\tdocker compose run --rm backend-test pytest\n'
    assert detect_root_repo_mounts(source, 'Makefile') == []


def test_matches_dollar_pwd_and_subpath():
    source = '\tdocker run --rm -v $PWD/frontend:/app node sh -c "npm ci"\n'
    assert len(detect_root_repo_mounts(source, 'script.sh')) == 1


def test_joins_backslash_continuations():
    source = (
        'target:\n'
        '\t@docker run --rm \\\n'
        '\t  -v "$(PWD)":/repo \\\n'
        '\t  python:3.14-slim sh -c "pip install -e ."\n'
    )
    violations = detect_root_repo_mounts(source, 'Makefile')
    assert len(violations) == 1
    assert violations[0][1] == 2


def test_continuation_with_user_is_accepted():
    source = (
        'target:\n'
        '\t@docker run --rm \\\n'
        '\t  --user $(shell id -u):$(shell id -g) \\\n'
        '\t  -v "$(PWD)":/repo img cmd\n'
    )
    assert detect_root_repo_mounts(source, 'Makefile') == []


def test_disable_comment_silences_the_file():
    source = (
        '# docker-run-host-user: disable\n'
        '\tdocker run --rm -v "$(PWD)":/w img cmd\n'
    )
    assert detect_root_repo_mounts(source, 'Makefile') == []
