## Description

<!-- Describe the changes introduced by this PR. -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring / code cleanup
- [ ] CI/CD / tooling

## Related issues

<!-- List issues closed by this PR. Use "Closes #<id>" syntax. -->

Closes #

## Checklist

- [ ] Tests added or updated (all 267 tests pass)
- [ ] `ruff check --config=config-tools/ruff.toml pre_commit_hooks tests` passes
- [ ] `ruff format --config=config-tools/ruff.toml pre_commit_hooks` applied
- [ ] Type annotations complete on all public functions
- [ ] README updated if the change adds or modifies a hook
- [ ] `.pre-commit-hooks.yaml` updated if a new hook was added
- [ ] `setup.cfg` entry point added for new hooks

## Testing

<!-- Describe how the changes were tested. -->

```bash
python3 -m pytest tests/ -q
ruff check --config=config-tools/ruff.toml pre_commit_hooks tests
```
