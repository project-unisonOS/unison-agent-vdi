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
Env vars: `VDI_SERVICE_PORT` (default 8083), `EXPERIENCE_RENDERER_URL`, `INTENT_GRAPH_URL`.

## Testing
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OTEL_SDK_DISABLED=true python -m pytest
```

## Integration
- Probes renderer `/readyz` and intent-graph `/health` for readiness.
- Included in `unison-devstack/docker-compose.yml`.

## Docs

Full docs at https://project-unisonos.github.io
