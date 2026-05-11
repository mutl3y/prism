# Scout: Layer Coupling Findings (discovery)\n\nGenerated: Mon 11 May 13:12:35 UTC 2026\n\n## Summary\n\n- Core→Extract violations: 0 occurrences\n- Extract→Plugins imports: 0 occurrences\n- Plugins→Core imports: 0 occurrences\n\n
## Core→Extract (scanner_core importing scanner_extract) — examples
\n- (none)\n
\n## Extract→Plugins (scanner_extract importing scanner_plugins) — examples
\n- (none)\n
\n## Plugins→Core (scanner_plugins importing scanner_core) — examples
\n- (none)\n
\n## All scanner import summary (unique lines + counts)

-       1 src/prism/tests/test_scanner_readme_init.py:import prism.scanner_readme as scanner_readme
-       1 src/prism/scanner_extract/task_catalog_assembly.py:import prism.scanner_extract.task_file_traversal as tft
-       1 src/prism/scanner_extract/task_catalog_assembly.py:import prism.scanner_extract.task_annotation_parsing as tap
-       1 src/prism/api_layer/cli_io.py:import prism.scanner_io as scanner_io
\n---\nArtifact written to: docs/plan/post-g84-arch-refactor-20260511/artifacts/scout-layer-coupling-findings.md
