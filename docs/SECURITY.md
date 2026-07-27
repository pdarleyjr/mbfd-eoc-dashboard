# Security and Privacy

- Private GitHub repository and Cloudflare Access-protected production hostname.
- Host publication only on `127.0.0.1:8220`; data stores and AI/browser services
  have no public ports.
- Non-root API/worker, read-only root filesystem, `no-new-privileges`, bounded
  tmpfs, minimal runtime image, restrictive CSP, trusted hosts, correlation IDs,
  rate limits, and generic user errors.
- Production API documentation disabled; operational endpoints are GET-only.
- PostgreSQL/Redis passwords are generated per deployment and `.env` is mode 0600.
- Dependency audit, Ruff, MyPy, ESLint, test coverage, container build, pip-audit,
  and Gitleaks run in CI.

The application stores public source records only. It excludes PHI, patient,
victim, responder and caller PII, medical narratives, private AVL/CAD/SCADA,
individual FPL customer data, private cookies and authorization headers.

Secret rotation: generate the replacement in the owning service, update only the
server `.env`/provider restriction, redeploy, verify, then revoke the previous
credential. Never print values; use fingerprints for diagnostics.
