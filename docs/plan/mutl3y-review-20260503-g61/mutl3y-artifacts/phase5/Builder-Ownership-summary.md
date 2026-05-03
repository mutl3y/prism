Builder-Ownership

- Scope: api scan-pipeline isolation ownership for G61-H01.
- Change: moved scan-pipeline registry isolation behind api_layer/plugin_facade with typed registry and factory protocols; api.py now consumes the facade seam instead of owning object-typed proxy helpers.
- Guardrail: added an API entrypoint regression that fails if api.py reintroduces local isolation helpers or bypasses the plugin_facade seam.
- Behavior: preserved scan_context isolation by copying the preflight context before plugin execution.
