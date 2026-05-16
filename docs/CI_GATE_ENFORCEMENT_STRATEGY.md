# CI Gate Enforcement: Local vs GitHub Integration

**Quick Answer**: ✅ **YES, CI gates CAN be enforced locally** - in fact, we recommend local enforcement as a first defense to save CI/CD minutes and provide immediate feedback.

## Two-Layer Enforcement Strategy

```
Developer Local (Fast Feedback)
    ↓
GitHub CI/CD (Final Validation)
```

---

## Option 1: Local CI Gate Enforcement (Recommended for Development)

### Quick Start

```bash
# Run all gates locally
python3 scripts/run_ci_gates_local.py

# Run specific gates
python3 scripts/run_ci_gates_local.py --gates mypy,ruff,black

# Verbose output for debugging
python3 scripts/run_ci_gates_local.py --verbose

# Stop on first failure
python3 scripts/run_ci_gates_local.py --fail-fast
```

### Available Gates

| Gate | Command | Purpose |
|------|---------|---------|
| `mypy` / `types` | Type checking | Strict type safety validation |
| `ruff` / `lint` | Linting | Code style, imports, unused variables |
| `black` / `format` | Formatting | Code formatting consistency |
| `layer` / `boundaries` | Layer boundaries | Prevents upward imports |
| `pytest` / `tests` | Test suite | Quick smoke test (critical tests only) |

### Example Output

```
🚀 Running Local CI Gates
==================================================

📝 Type Safety (mypy)... ✅
🔍 Linting (ruff)... ✅
🎨 Formatting (black)... ✅
🏗️  Layer Boundaries... ✅
⚡ Tests (quick)... ✅

==================================================

📊 Summary: 5/5 gates passed
✅ Ready to push!
```

### When a Gate Fails

```bash
# See detailed failure info
python3 scripts/run_ci_gates_local.py --verbose

# Fix specific issues
black src/prism/                    # Auto-fix formatting
ruff check src/prism/ --fix         # Auto-fix linting
python3 -m mypy --strict src/       # See type errors

# Re-run gates after fixes
python3 scripts/run_ci_gates_local.py
```

---

## Option 2: Pre-Commit Hook Integration (Automatic Local Check)

### Setup (One-time)

```bash
# 1. Install pre-commit if not already installed
pip install pre-commit

# 2. Create .pre-commit-config.yaml in repo root
# (See template below)

# 3. Install hooks
pre-commit install

# 4. Test
pre-commit run --all-files
```

### Pre-Commit Configuration Template

Create `.pre-commit-config.yaml` in repo root:

```yaml
repos:
  # Local Python-based gates
  - repo: local
    hooks:
      - id: ci-gates-local
        name: CI Gates (Local)
        entry: python3 scripts/run_ci_gates_local.py
        language: system
        types: [python]
        stages: [commit]
        
      - id: mypy-strict
        name: Type Safety (mypy)
        entry: .venv/bin/python -m mypy --strict src/prism/scanner_core/
        language: system
        types: [python]
        stages: [commit]
        pass_filenames: false
        
      - id: ruff-check
        name: Linting (ruff)
        entry: .venv/bin/python -m ruff check src/prism/
        language: system
        types: [python]
        stages: [commit]
        pass_filenames: false
        
      - id: black-check
        name: Formatting (black)
        entry: .venv/bin/python -m black --check src/prism/
        language: system
        types: [python]
        stages: [commit]
        pass_filenames: false

  # Third-party tools
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
```

### Usage with Pre-Commit Hook

```bash
# Automatically runs on commit
git add .
git commit -m "fix: resolve type safety issues"
# → Hook runs automatically, prevents commit if gates fail

# Run manually anytime
pre-commit run --all-files

# Bypass for emergencies (NOT recommended)
git commit --no-verify
```

---

## Option 3: GitHub Actions CI/CD Integration (Enforcement Gating)

### GitHub Actions Workflow

Create `.github/workflows/ci-gates.yml`:

```yaml
name: CI Gates

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

permissions:
  contents: read
  pull-requests: write

jobs:
  ci-gates:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Run CI Gates Locally
        run: python3 scripts/run_ci_gates_local.py --verbose
        continue-on-error: true
      
      - name: Type Safety (mypy --strict)
        run: .venv/bin/python -m mypy --strict src/prism/scanner_core/
      
      - name: Linting (ruff)
        run: .venv/bin/python -m ruff check src/prism/
      
      - name: Formatting (black)
        run: .venv/bin/python -m black --check src/prism/
      
      - name: Layer Boundary Enforcement
        run: |
          if grep -r "from prism.scanner_plugins" src/prism/scanner_core/; then
            echo "❌ Layer boundary violation: scanner_core cannot import scanner_plugins"
            exit 1
          fi
      
      - name: Test Suite
        run: |
          python -m pytest src/prism/tests/ -x -q \
            --tb=short \
            --disable-warnings
      
      - name: Coverage Report
        run: |
          python -m pytest src/prism/tests/ \
            --cov=src/prism/ \
            --cov-fail-under=80 \
            --cov-report=term-missing
      
      - name: Report Status
        if: always()
        run: |
          echo "## ✅ CI Gate Status" >> $GITHUB_STEP_SUMMARY
          echo "All gates passed - PR is ready for merge" >> $GITHUB_STEP_SUMMARY
```

### Block PR on Failure

GitHub Settings:

```
Repo → Settings → Branches → Branch Protection Rules

For 'main':
  ✅ Require status checks to pass before merging
    → Select "ci-gates" workflow
  ✅ Require code reviews before merging (1+ approval)
  ✅ Require branches to be up to date before merging
```

---

## Recommended Workflow: Local + GitHub Two-Layer

### Developer Workflow

```bash
# 1. Make changes
git checkout -b feat/my-feature
# ... edit code ...

# 2. Run local gates BEFORE committing
python3 scripts/run_ci_gates_local.py

# If any gates fail:
python3 scripts/run_ci_gates_local.py --verbose  # See details
black src/prism/                                  # Auto-fix formatting
ruff check src/prism/ --fix                      # Auto-fix linting
python3 -m pytest src/prism/tests/ -xvs          # Run full tests

# 3. Commit and push
git add .
git commit -m "feat: my feature"
git push origin feat/my-feature

# 4. GitHub Actions runs gates again as final validation
# (catches environment-specific issues, provides audit trail)

# 5. PR review → merge
```

### Benefits of Two-Layer Strategy

| Aspect | Local | GitHub |
|--------|-------|--------|
| **Speed** | Instant (2-5 sec) | 1-3 minutes |
| **Cost** | Free (local machine) | Uses CI minutes |
| **Feedback** | Immediate for dev | Audit trail for team |
| **Enforcement** | Soft (easy to bypass) | Hard (blocks PR merge) |
| **Environments** | Single (dev machine) | Multiple (matrix testing) |

**Recommendation**: Use local gates to catch issues fast during development, GitHub gates for final enforcement before merge.

---

## Cost Optimization

### Before (All GitHub)
- Every code change → GitHub runs full suite
- 5-10 commits per day × 3 min/run = 50-100 CI minutes/day
- **Cost: High CI/CD minute overhead**

### After (Local + GitHub)
- Developers catch 80% of issues locally (instant)
- Only 20% reach GitHub (serious issues only)
- Reduced CI minute usage by ~70%
- **Cost: Minimal CI/CD overhead + faster feedback**

---

## Troubleshooting

### "Local gates pass but GitHub fails"

→ Check Python version mismatch:
```bash
# Local
python --version

# GitHub runner (from logs)
python -m sys.version

# Fix: Update GitHub workflow to use same version
```

→ Check venv vs system Python:
```bash
# Use venv Python explicitly
.venv/bin/python -m mypy --strict src/
```

### "Gate bypassed accidentally"

→ Pre-commit didn't run:
```bash
# Re-install hooks
pre-commit install --install-hooks

# Reinstall after upgrading
pre-commit clean
pre-commit install
```

### "How to skip gates for hotfix?"

Emergency-only (use sparingly):
```bash
# Local
python3 scripts/run_ci_gates_local.py --skip-gates

# Pre-commit hook
git commit --no-verify

# GitHub (not recommended, requires override)
# Contact repo maintainer for emergency merge
```

---

## Summary: Local vs GitHub Enforcement

| Method | Setup Time | Speed | Enforcement | Recommended For |
|--------|------------|-------|-------------|-----------------|
| **Direct Command** | 30 sec | 2-5 sec | Soft | Daily development |
| **Pre-Commit Hook** | 2 min | 2-5 sec | Medium | Team adoption |
| **GitHub Actions** | 5 min | 1-3 min | Hard | Final validation |
| **Both (Recommended)** | 5 min | 2-5 + 1-3 | Hard | Production-grade |

**Choose your approach:**
- 🚀 **Quick start**: `python3 scripts/run_ci_gates_local.py`
- 🔐 **Team enforcement**: Add pre-commit hooks
- 📊 **Audit trail**: Use GitHub Actions for final gate
- ✅ **Best practice**: All three together

---

## Next Steps

1. **Today**: Try local enforcement
   ```bash
   python3 scripts/run_ci_gates_local.py
   ```

2. **This week**: Add pre-commit hooks
   ```bash
   pip install pre-commit
   # Copy .pre-commit-config.yaml from template above
   pre-commit install
   ```

3. **This sprint**: Deploy GitHub Actions workflow
   ```bash
   # Copy ci-gates.yml workflow to .github/workflows/
   # Enable branch protection with status checks
   ```

4. **Ongoing**: Run local gates before pushing
   ```bash
   python3 scripts/run_ci_gates_local.py && git push
   ```

---

**Questions?**

- Full local gate help: `python3 scripts/run_ci_gates_local.py --help`
- CI gate details: See `scripts/validate_ci_gates.py`
- Pre-commit docs: https://pre-commit.com/
- GitHub Actions docs: https://docs.github.com/en/actions
