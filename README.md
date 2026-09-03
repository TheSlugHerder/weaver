# Weaver

Minimal scaffold for a FastAPI-based game engine. See the deployment guide for production instructions: [DEPLOYMENT.md](DEPLOYMENT.md)

Please do not commit local virtual environments or absolute local paths. Use a project-local virtualenv (e.g. `.venv`) and ensure `.gitignore` excludes it. See `weaver.env.sample` and `DEPLOYMENT.md` for deployment guidance.

## Current Status

- Branch: `fix/clear-secret-sample` (PR open)
- CI: `CI` workflow re-enabled for lint (`ruff`) and security (`bandit`); a run is in progress.
- Local tests: all unit tests pass locally (16 passed, 1 skipped at time of update).
- Lint: `ruff --fix` run and auto-fixes applied; remaining issues addressed where safe.
- Next steps: wait for CI to finish; if it passes, merge the PR and re-enable any additional checks or hardening steps as needed.

If you need me to merge the PR when CI passes, or to continue fixing any lint/security findings, tell me and I'll proceed.

Security findings: Bandit reported 22 low-severity issues; see [bandit_low_issues.md](bandit_low_issues.md) for details and recommendations.
