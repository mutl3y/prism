agent: Foreman-Fallback
owned_file_set:

- src/prism/scanner_core/di.py

status: completed
changed_files:

- src/prism/scanner_core/di.py

The live narrow gate surfaced an `IndentationError` in `DIContainer.__init__` before any
builder wave was worth dispatching. The fallback repair restored the indentation of
`self._registry: PluginRegistry | None = registry` so the constructor body is syntactically
valid again. The same focused DI pytest slice was rerun into `.mutl3y-gate/live-di-wave1-narrow.log`
and passed cleanly aside from one existing stateless-warning on the ansible scan-pipeline plugin.
