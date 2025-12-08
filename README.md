# unison-agent-vdi

Thin VDI/desktop agent that fronts the experience renderer and intent graph for remote display/control use cases.

## Status
Optional (active) — runs in devstack on `8093`; can be omitted if using other shells.

## Run
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
cp .env.example .env
python src/main.py
```
Env vars:
- `VDI_SERVICE_PORT` (default 8083)
- `VDI_SERVICE_TOKEN` (auth from actuation)
- `EXPERIENCE_RENDERER_URL`, `INTENT_GRAPH_URL`
- `VPN_HEALTH_URL` (e.g., `http://localhost:8084/readyz`)
- `VDI_REQUIRE_VPN` (default `true`)
- `STORAGE_URL` / `STORAGE_TOKEN` for artifact upload
- `VDI_WORKSPACE_PATH` (default `/workspace`)
- `VDI_FAKE_BROWSER=true` to stub Playwright in tests

## Testing
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OTEL_SDK_DISABLED=true python -m pytest
```

## Integration
- Exposes `/tasks/browse`, `/tasks/form-submit`, `/tasks/download` for actuation.
- Probes renderer `/readyz`, intent-graph `/health`, and VPN `/readyz` for readiness.
- Included in `unison-devstack/docker-compose.yml` sharing the `unison-network-vpn` network namespace.

## Open tasks (VDI/VPN)
- Storage/audit: replace KV upload shim with real storage file uploads; enrich audit with decision IDs, exit IP, domain; clean workspace after upload.
- Policy/consent/auth: enforce JWT verification via `unison-auth`, consent references, and risk/scope gating across orchestrator → actuation → VDI.
- Orchestrator wiring: update orchestrator/tooling to invoke actuation `/vdi/tasks/*` with documented payloads tied to skills/intents.
- Security compose: mirror VPN/VDI wiring into `docker-compose.security.yml` with segmented networks.
- CI/CD: add agent-vdi unit tests (with `VDI_FAKE_BROWSER=true`), build/publish VPN image tags, optional mini-stack integration asserting VPN readyz + VDI health with a test WG config.
- Browser robustness: add retries/backoff, domain allow/deny controls, and credential/cookie handling via storage vault references.

## Docs

Full docs at https://project-unisonos.github.io
